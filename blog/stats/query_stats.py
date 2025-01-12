from collections import Counter
from django.forms.models import model_to_dict
from blog.models import SearchQueryLog, List
import re
from typing import Dict, Set, Tuple
from ipaddress import ip_address
import Levenshtein  


class StatsGenerator:
    def __init__(self):
        self.models = {
            'search': {'model': SearchQueryLog, 'field': 'query'},
            'list': {'model': List, 'field': 'input'}
        }

        # Common spam or nonsense patterns
        self.spam_patterns = [
            r'^[a-z]$',  # Single letters
            r'^[0-9]+$',  # Just numbers
            r'^[!@#$%^&*()]+$',  # Just symbols
            r'^\s*$',  # Just whitespace
            r'^(test|asdf|qwerty|abc|xyz)',  # Common test inputs
            r'(.)\1{4,}',  # Repeated characters (e.g., 'aaaaa')
        ]
        
        # Known name prefixes to help identify names
        self.name_prefixes = {'mr', 'mrs', 'ms', 'dr', 'prof'}

    
    def get_query_stats(self):
        """Get statistics for search queries"""
        return Counter(
            SearchQueryLog.objects.values_list('query', flat=True)
        )
    
    def get_list_stats(self):
        """Get statistics for list entries"""
        return Counter(
            List.objects.values_list('input', flat=True)
        )
    
    def get_stats_by_ip(self, model_name):
        """
        Get statistics by IP address for a given model and field.
        Counts how many unique IPs have interacted with each term.
        """
        model_dict = self.models.get(model_name)
        model = model_dict['model']
        field = model_dict['field']

        if not model:
            raise ValueError(f"Invalid model name: {model_name}")
            
        # Track IPs per term
        term_ips = {}
        
        # Collect all IPs for each term
        for obj in model.objects.all():
            if obj.ip_address:  # Only count if IP exists
                obj_dict = model_to_dict(obj)
                term = obj_dict[field]
                if term not in term_ips:
                    term_ips[term] = set()
                term_ips[term].add(obj.ip_address)
        
        # Convert sets of IPs to counts
        return Counter({
            term: len(ips) 
            for term, ips in term_ips.items()
        })

    def clean_term(self, term: str) -> str:
        """Clean and standardize a term"""
        if not term or not isinstance(term, str):
            return ""
        # Convert to uppercase and strip whitespace
        term = term.upper().strip()
        # Remove special characters
        term = re.sub(r'[^\w\s]', '', term)
        return term
        
    def is_likely_name(self, term: str) -> bool:
        """Check if a term is likely to be a name"""
        # Remove common prefixes
        term_lower = term.lower()
        for prefix in self.name_prefixes:
            if term_lower.startswith(prefix + ' '):
                term = term[len(prefix)+1:]
                break
                
        # Check for capitalized words
        words = term.split()
        if len(words) >= 1 and all(word.istitle() for word in words):
            return True
            
        return False
        
    def is_spam(self, term: str) -> bool:
        """Check if a term matches spam patterns"""
        term = term.lower().strip()
        
        # Check against spam patterns
        for pattern in self.spam_patterns:
            if re.match(pattern, term):
                return True
                
        # Check for random character sequences
        if len(term) > 3:
            unique_chars = len(set(term))
            if unique_chars / len(term) > 0.8:  # High ratio of unique characters
                return True
                
        return False
        
    def group_similar_terms(self, terms: Counter) -> Counter:
        """Group similar terms and combine their counts"""
        grouped = Counter()
        processed = set()
        
        # Sort terms by count (process more frequent terms first)
        sorted_terms = sorted(terms.items(), key=lambda x: x[1], reverse=True)
        
        for term, count in sorted_terms:
            if term in processed:
                continue
                
            clean_term = self.clean_term(term)
            if not clean_term or len(clean_term) <= 1:
                continue
                
            if self.is_spam(clean_term):
                continue
                
            if not self.is_likely_name(term):
                continue
                
            # Find similar terms
            similar_terms = {term}
            term_parts = clean_term.split()
            
            for other_term, other_count in sorted_terms:
                if other_term in processed:
                    continue
                    
                other_clean = self.clean_term(other_term)
                other_parts = other_clean.split()
                
                # Check if terms are related (e.g., "James" and "James Aaronson")
                if len(term_parts) == 1 and len(other_parts) > 1:
                    if term_parts[0] == other_parts[0]:
                        similar_terms.add(other_term)
                elif len(other_parts) == 1 and len(term_parts) > 1:
                    if other_parts[0] == term_parts[0]:
                        similar_terms.add(other_term)
                elif Levenshtein.ratio(clean_term, other_clean) > 0.9:
                    similar_terms.add(other_term)
                    
            # Add to processed set
            processed.update(similar_terms)
            
            # Combine counts
            total_count = sum(terms[t] for t in similar_terms)
            # Use the longest term as the canonical form
            canonical_term = max(similar_terms, key=len)
            grouped[canonical_term] = total_count
            
        return grouped
        
    def analyze_ip_patterns(self, model_name: str) -> Dict[str, Set[str]]:
        """
        Analyze IP patterns to identify potentially related IPs.
        Returns dict mapping groups of related IPs to their terms.
        """
        model_dict = self.models.get(model_name)
        model = model_dict['model']
        ip_patterns = {}
        
        # Group IPs by subnet
        for obj in model.objects.all():
            if not obj.ip_address:
                continue
                
            try:
                ip = ip_address(obj.ip_address)
                # Group by /24 subnet for IPv4
                if ip.version == 4:
                    subnet = str(ip).rsplit('.', 1)[0]
                    if subnet not in ip_patterns:
                        ip_patterns[subnet] = set()
                    ip_patterns[subnet].add(obj.ip_address)
            except ValueError:
                continue
                
        return ip_patterns

    def get_stats_by_ip_with_patterns(self, model_name: str):
        """
        Get statistics by IP address, treating IPs from the same subnet as one user.
        """
        model_dict = self.models.get(model_name)
        model = model_dict['model']
        field = model_dict['field']

        # First get subnet patterns
        ip_patterns = self.analyze_ip_patterns(model_name)
        
        # Track terms by subnet instead of individual IPs
        term_subnets = {}
        
        for obj in model.objects.all():
            if not obj.ip_address:
                continue
            
            try:
                ip = ip_address(obj.ip_address)
                if ip.version == 4:
                    subnet = str(ip).rsplit('.', 1)[0]  # Get /24 subnet
                    term = getattr(obj, field)
                    
                    if term not in term_subnets:
                        term_subnets[term] = set()
                    term_subnets[term].add(subnet)
            except ValueError:
                continue
        
        # Convert subnet sets to counts
        return Counter({
            term: len(subnets)
            for term, subnets in term_subnets.items()
        })

    def get_enhanced_stats(self, model_name: str):
        raw_counts = self.get_stats_by_ip(model_name)
        return self.group_similar_terms(raw_counts)

    def get_enhanced_stats_by_ip(self, model_name: str):
        stats_by_patterns = self.get_stats_by_ip_with_patterns(model_name)
        return self.group_similar_terms(stats_by_patterns)


    def generate_report(self, output_file="stats_report.txt"):
        """Generate a complete statistics report"""
        with open(output_file, "a+") as f:
            query_stats = self.get_query_stats()
            self._write_section(f, "Query Stats", query_stats)
            list_stats = self.get_list_stats()
            self._write_section(f, "List Stats", list_stats)
            combined_stats = query_stats + list_stats
            self._write_section(f, "Combined Query and List Stats", combined_stats)

            list_ip_counts = self.get_stats_by_ip('list')
            query_ip_counts = self.get_stats_by_ip('search')
            self._write_section(f, "List IP Stats", 
                              list_ip_counts)
            self._write_section(f, "Query IP Stats", 
                              query_ip_counts)
            
            # Combined IP stats
            self._write_section(f, "Combined IP Stats", list_ip_counts + query_ip_counts)
            self._write_section(f, "Enhanced List Stats", self.get_enhanced_stats('list'))
            self._write_section(f, "Enhanced Query Stats", self.get_enhanced_stats('search'))
            self._write_section(f, "Enhanced Combined Stats", self.get_enhanced_stats('search') + self.get_enhanced_stats('list'))
            self._write_section(f, "Enhanced List IP Stats", self.get_enhanced_stats_by_ip('list'))
            self._write_section(f, "Enhanced Query IP Stats", self.get_enhanced_stats_by_ip('search'))
            self._write_section(f, "Enhanced Combined IP Stats", self.get_enhanced_stats_by_ip('search') + self.get_enhanced_stats_by_ip('list'))

    def _write_section(self, file, title, counter):
        """Helper method to write a section of the report"""
        file.write(f"\n{'-'*100}\n")
        file.write(f"{title}\n")
        file.write(f"{'-'*100}\n")
        sorted_counter = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        for item, count in sorted_counter:
            file.write(f"{item} -- {count}\n")