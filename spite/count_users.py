import re
from datetime import datetime
from django.utils import timezone

def get_ip_from_log(log):
    '''
    Extract IP address from the log entry.
    
    Log patterns:
    2024-08-28 04:29:09 -- 73.165.53.165--- get-post
    2024-08-28 04:30:01 -- 174.206.164.175
    '''
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

    re_match = re.search(ip_pattern, log)
    if re_match:
        ip_address = re_match.group()
        return ip_address
    else:
        return None

def extract_datetime_from_log(log):
    '''
    Extract datetime from the log entry.
    
    Log patterns:
    2024-08-28 04:29:09 -- 73.165.53.165--- get-post
    2024-08-28 04:30:01 -- 174.206.164.175
    '''
    datetime_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    re_match = re.search(datetime_pattern, log)
    if re_match:
        try:
            log_datetime = datetime.strptime(re_match.group(), "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            pass
        return log_datetime
    else:
        return None

current_timezone = timezone.get_current_timezone() 
def count_ips(logfile, past_time=None):
    unique_ips = set()

    try:
        with open(logfile) as f:
            logs = f.readlines()
            for log in logs:
                log_datetime = extract_datetime_from_log(log)
            
                if past_time is None or \
                    (log_datetime is not None and \
                        timezone.make_aware(log_datetime, current_timezone)  >= past_time):
                    ip = get_ip_from_log(log)
                    if ip:
                        unique_ips.add(ip)
    except FileNotFoundError:
        pass

    return len(unique_ips)

