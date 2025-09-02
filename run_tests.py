#!/usr/bin/env python
"""
Test runner for context processor and cache functionality tests.
Run this to ensure pagination and post attributes work properly.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spite.settings')
    django.setup()

def run_tests():
    """Run the tests"""
    setup_django()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run specific test modules
    test_modules = [
        'blog.tests.test_context_processors',
        'blog.tests.test_cache_functionality',
    ]
    
    print("🧪 Running Context Processor and Cache Tests...")
    print("=" * 60)
    
    failures = test_runner.run_tests(test_modules)
    
    if failures:
        print(f"\n❌ {failures} test(s) failed!")
        return False
    else:
        print("\n✅ All tests passed!")
        return True

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
