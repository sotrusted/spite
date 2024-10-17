import re
from datetime import datetime
from django.utils import timezone
import subprocess
import logging 
import apache_log_parser
from django.utils import timezone
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
import logging

logger = logging.getLogger('spite')

# Define the log format for Nginx logs
log_format = '%h %l %u %t \"%r\" %>s %b'

# Create the log parser object based on the format
parser = apache_log_parser.make_parser(log_format)

logger = logging.getLogger('spite')

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
            return log_datetime
        except:
            pass

    return None

def extract_datetime_from_log(log):
    datetime_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    re_match = re.search(datetime_pattern, log)
    if re_match:
        try:
            return datetime.strptime(re_match.group(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Log or handle the error if the datetime cannot be parsed
            return None
    return None

current_timezone = timezone.get_current_timezone() 
def count_ips(logfile, start_time=None):
    """
    Count unique IPs from Nginx access logs after a given start_time, using subprocess to read logs.

    Args:
    logfile (str): Path to the Nginx access log file.
    start_time (datetime): The datetime from which to start counting IPs. If None, count all IPs.

    Returns:
    int: The number of unique IPs found after the start_time.
    """
    unique_ips = set()

    try:
        # Use subprocess to stream the log file using 'cat' to avoid loading it into memory
        command = ['cat', logfile]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        logtext = process.stdout.read()
        loglines = logtext.splitlines()


        for logline in loglines:
            try:
                if logline.count('[') != 2 or logline.count(']') != 2:
                    logger.error(f"Malformed log line detected: {logline.strip()}")
                    continue
                # Parse the logline using apache-log-parser
                log_data = parser(logline)
                
                # Extract the IP and time
                log_ip = log_data['remote_host']
                log_time_str = log_data['time_received']

                # Remove square brackets from the time string
                log_time_str = log_time_str.strip('[]')

                # Convert the log time to a datetime object
                log_time = datetime.strptime(log_time_str, '%d/%b/%Y:%H:%M:%S %z')
                logger.info(log_time)
                
                # Check if the log time is after the provided start_time
                if start_time is None or log_time >= start_time:
                    unique_ips.add(log_ip)
            except apache_log_parser.LineDoesntMatchException as e:
                # Skip lines that don't match the expected log format
                logger.error(f"Line {logline} does not match. Error: {e}")
                continue
            except Exception as e:
                logger.error(f"Failed to parse log line: {logline}. Error: {e}")

        # Ensure the subprocess exits cleanly
        process.stdout.close()
        process.wait()

    except FileNotFoundError:
        logger.error(f"Log file not found: {logfile}")
    except Exception as e:
        logger.error(f"Unexpected error while processing the log file: {e}")

    return len(unique_ips)