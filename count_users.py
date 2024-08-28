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

if __name__ == '__main__':
    with open('iplog') as f:
        logs = f.readlines()
        ips = [x for x in [get_ip_from_log(log) for log in logs] if x]
        print(len(set(ips)))
        
    
