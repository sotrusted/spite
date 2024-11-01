import os
import json
import folium
import re
import requests

# Regex pattern for IPv4
ipv4_pattern = re.compile(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

# Path to the JSON file
json_file_path = 'ip_locations.json'

# Path to the log file 
logfile = 'django_access.log'

# IPInfo API token 
api_token = '040a90a07df957'

# Function to read IP addresses and their locations from the JSON file
def read_ip_locations(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

# Function to write IP addresses and their locations to the JSON file
def write_ip_locations(file_path, ip_locations):
    with open(file_path, 'w') as file:
        json.dump(ip_locations, file, indent=4)

def is_valid_ipv4(ip):
    return ipv4_pattern.match(ip) is not None

def get_ip_addresses(logfile):
    with open(logfile, 'r') as f:
        ips = [line.split()[0].strip() for line in f.read().splitlines()]
        ips = list(filter(is_valid_ipv4, ips))
    return ips

# Function to get location data from ipinfo.io
def get_location(ip):
    response = requests.get(f'http://ipinfo.io/{ip}?token={api_token}')
    data = response.json()
    print(f'ip data: {data}')
    return {
        'ip': ip,
        'city': data.get('city', 'N/A'),
        'region': data.get('region', 'N/A'),
        'country': data.get('country', 'N/A'),
        'loc': data.get('loc', 'N/A')
    }

# Function to add a new IP address and its location to the JSON file
def add_ip_location(ip_locations, new_ip):
    if new_ip not in ip_locations:
        location_data = get_location(new_ip)
        ip_locations[new_ip] = location_data
        write_ip_locations(json_file_path, ip_locations)
        print(f"IP address {new_ip} and its location added.")
    else:
        print(f"IP address {new_ip} already exists.")


# Function to create a map with IP addresses and their locations
def create_map(ip_addresses):
    # Create a map centered around a default location
    map_center = [0, 0]  # Default center of the map (latitude, longitude)
    mymap = folium.Map(location=map_center, zoom_start=2)

    # Read location data from the JSON file
    ip_locations = read_ip_locations(json_file_path)


    # Get location data for each IP address and add a marker to the map
    for ip in ip_addresses:
        if ip in ip_locations:
            location_data = ip_locations[ip]
            if 'loc' in location_data:
                lat, lon = map(float, location_data['loc'].split(','))
                folium.Marker(
                    location=[lat, lon],
                    popup=f"IP: {ip}\nCity: {location_data.get('city', 'N/A')}\nRegion: {location_data.get('region', 'N/A')}\nCountry: {location_data.get('country', 'N/A')}",
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(mymap)

    # Save the map to an HTML file
    mymap.save('ip_locations_map.html')


def analyze_ip_locations(ip_locations):
    num_ips = len(ip_locations)
    cities = set()
    regions = set()
    countries = set()
    for ip in ip_locations:
        location = ip_locations[ip]
        cities.add(location['city'])
        regions.add(location['region'])
        countries.add(location['country'])
    return (num_ips, len(cities), len(regions), len(countries))

if __name__ == '__main__':

    ip_addresses = get_ip_addresses(logfile)

    ip_locations = read_ip_locations(json_file_path)

    print(f'ip_locations: {ip_locations}')
    # Add IP addresses and their locations to the JSON file
    for ip in ip_addresses:
        add_ip_location(ip_locations, ip)

    # Create the map with the IP addresses
    # create_map(ip_addresses)

    print(analyze_ip_locations(ip_locations))
