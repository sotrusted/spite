import re 
def get_ip_from_log(log):
    '''
    log patterns
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

def count_ips(logfile):
    unique_ips = set()

    try:
        with open(logfile) as f:
            logs = f.readlines()
            for log in logs:
                ip = get_ip_from_log(log)
                if ip:
                    unique_ips.add(ip)
    except FileNotFoundError:
        pass

    return len(unique_ips)

