import streamlit as st
import json
import pandas as pd
import requests
import os
import math

from openai import OpenAI

import folium
from streamlit_folium import folium_static
from twilio.rest import Client

from datetime import datetime
from datetime import time
from zoneinfo import ZoneInfo

timezone = ZoneInfo('America/Los_Angeles')

def get_time_score(current_datetime, shelter):
    current_day = current_datetime.strftime("%A")
    
    if current_day not in shelter['Days']:
        return 1

    weekday = current_datetime.weekday()

    current_hour = current_datetime.strftime("%H")
    current_minute = current_datetime.strftime("%M")
    current_time = time(int(current_hour), int(current_minute))

    hour_start = shelter['Hour Start'].split(',')
    minute_start = shelter['Minute Start'].split(',')
    shelter_start = time(int(hour_start[weekday]), int(minute_start[weekday]))

    hour_end = shelter['Hour End'].split(',')
    minute_end = shelter['Minute End'].split(',')
    shelter_end = time(int(hour_end[weekday]), int(minute_end[weekday]))

    if shelter_start < shelter_end:
        if shelter_start <= current_time <= shelter_end: return 0
        else: return 1
    else:
        if current_time >= shelter_start or current_time <= shelter_end: return 0
        else: return 1

def geocode_address(address, api_key):
    # URL encode the address
    encoded_address = requests.utils.quote(address)

    # Send a request to the Google Maps Geocoding API
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    response = requests.get(geocode_url)
    data = response.json()

    lat = data['results'][0]['geometry']['location']['lat']
    lon = data['results'][0]['geometry']['location']['lng']
    return round(lat, 6), round(lon, 6)

# Reference: https://github.com/sfc38/Google-Maps-API-Streamlit-App/blob/master/google_maps_app.py#L126-L135
def create_map():
    # Create the map with Google Maps
    map_obj = folium.Map(tiles=None)
    folium.TileLayer("https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 
                     attr="google", 
                     name="Google Maps", 
                     overlay=True, 
                     control=True, 
                     subdomains=["mt0", "mt1", "mt2", "mt3"]).add_to(map_obj)
    return map_obj

def call_gpt(user_needs, shelter_services, api_key):
    client = OpenAI(api_key = api_key)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Given two variables 'user needs' (the ideal qualities/services of a shelter) and 'shelter services' (the services offered by a shelter), return an integer 0-10 that scores how well the 'shelter services' match the 'user needs' where 0 is the best fit and 10 is the worst fit. IMPORTANT: NO MATTER WHAT, ONLY RETURN THE INTEGER (NO EXTRA WORDS, PUNCTUATION, ETC.)"},
            {"role": "user", "content": f"user_needs: {user_needs}, shelter_services: {shelter_services}"}
        ]
    )

    score = completion.choices[0].message.content.strip()
    return int(score)

def get_urgency_score(user, shelter):
    if user == "Today": 
        if shelter == "Immidiate": return 0
        if shelter == "High": return 0.75
        if shelter == "Moderate": return 1
    elif user == "In the next few days":
        if shelter == "Immidiate": return 0.25
        if shelter == "High": return 0
        if shelter == "Moderate": return 0.75
    elif user == "In a week or more":
        if shelter == "Immidiate": return 0.75
        if shelter == "High": return 0.25
        if shelter == "Moderate": return 0

def get_duration_score(user, shelter):
    if user == "Overnight":
        if shelter == "Overnight": return 0
        if shelter == "Temporary": return 0.5
        if shelter == "Transitional": return 0.75
        if shelter == "Long-Term": return 1
    elif user == "A month or less":
        if shelter == "Overnight": return 0.5
        if shelter == "Temporary": return 0
        if shelter == "Transitional": return 0.25
        if shelter == "Long-Term": return 0.75
    elif user == "A couple of months":
        if shelter == "Overnight": return 0.75
        if shelter == "Temporary": return 0.25
        if shelter == "Transitional": return 0
        if shelter == "Long-Term": return 0.5
    elif user == "A year or more":
        if shelter == "Overnight": return 1
        if shelter == "Temporary": return 0.75
        if shelter == "Transitional": return 0.5
        if shelter == "Long-Term": return 0
    
def get_coordinates(zipcode: str, api_key: str) -> list:
    """
    Get the coordinates (latitude and longitude) of an address using the OpenWeather Geocoding API.

    Parameters:
    zipcode (str): The zipcode to geocode.
    api_key (str): Your OpenWeather API key.

    Returns:
    list: A list containing the latitude and longitude of the address.
    """

    base_url = "http://api.openweathermap.org/geo/1.0/zip"
    params = {
        'zip': str(zipcode) + ",US",
        'appid': api_key
    }

    response = requests.get(base_url, params=params)
    data = response.json()
    return [data.get('lat'), data.get('lon')]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers. Use 3956 for miles.
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# Initialize session state
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

if 'shelter_index' not in st.session_state:
    st.session_state.shelter_index = 0

if 'shelters_filtered' not in st.session_state:
    st.session_state.shelters_filtered = False

# Page config
st.set_page_config(
    page_title="ShelterSearch",
    layout="wide",
)

st.title("ShelterSearch")

if not st.session_state.form_submitted:
    st.write("Hello there! Fill out this quick form to receive recommendation for where you can go to receive help.")
    st.markdown("Please give us feedback at this [link](https://forms.gle/oLMJ2qVc6HYgwfCw9)")

    # should be updated manually annually - use zipcodebase API
    zipcodes = {
        'San Francisco': ['94101', '94102', '94103', '94104', '94105', '94107', '94108', '94109', '94110', '94111', '94112', '94114', '94115', '94116', '94117', '94118', '94119', '94120', '94121', '94122', '94123', '94124', '94125', '94126', '94127', '94128', '94129', '94130', '94131', '94132', '94133', '94134', '94140', '94141', '94142', '94146', '94147', '94157', '94159', '94164', '94165', '94166', '94167', '94168', '94169', '94170', '94172', '94188'],
        'Oakland': ['94601', '94602', '94603', '94604', '94605', '94606', '94607', '94608', '94609', '94610', '94611', '94612', '94613', '94614', '94615', '94617', '94618', '94619', '94620', '94621', '94623', '94624', '94661', '94662'],
        'Berkeley': ['94701', '94702', '94703', '94704', '94705', '94706', '94707', '94708', '94709', '94710', '94712']
    }
    
    city = st.selectbox("City", ['San Francisco', 'Oakland', 'Berkeley'])
    zipcode = st.selectbox("Zipcode", ['Unsure'] + zipcodes[city])
        
    sex = st.radio("Sex", ["Male", "Female", "Other"])
    lgbtq = st.radio("Do you identify as LGBTQ+ (some shelters serve this community specifically)", ["No", "Yes"])
    domestic_violence = st.radio("Have you experienced domestic violence (some shelters serve these individuals specifically", ["No", "Yes"])
    
    urgency = st.radio("How quickly do you need help?", ("Today", "In the next few days", "In a week or more"))
    duration = st.radio("How long do you need a place to stay?", ("Overnight", "A month or less", "A couple of months", "A year or more"))
    needs = st.text_area("Optional - Needs (tell us what you need and how we can help)")

    phone_number = st.text_input('Optional - Enter your phone number (to text shelter info to you)', '+1')
    consent = st.checkbox('I consent to receiving a one-time message')

    if st.button("Submit"):
        data = {
            "City": city,
            "Zip Code": zipcode,
            "Sex": sex,
            "LGBTQ": lgbtq,
            "Domestic Violence": domestic_violence,
            "Urgency": urgency,
            "Duration": duration,
            "Needs": needs,
            "Phone Number": phone_number,
            "Consent": consent
        }

        with open('data.json', 'w') as f:
            json.dump(data, f)

        st.session_state.form_submitted = True
        st.rerun()
else:
    if not st.session_state.shelters_filtered:
        with open('data.json', 'r') as f:
            data = json.load(f)

        shelters = pd.read_csv("database.csv")
    
        # filter city
        shelters = shelters[(shelters['City'] == data['City'])]
        
        # filter sex
        shelters = shelters[(shelters['Sex'] == data['Sex']) | (shelters['Sex'] == 'All')]
    
        # filter lgbtq
        if data['LGBTQ'] == 'No':
            shelters = shelters[(shelters['LGBTQ'] == "No")]

        # filter domestic violence
        if data['Domestic Violence'] == "No":
            shelters = shelters[(shelters['Domestic Violence'] == "No")]
    
        # keep track of which scores are calculated
        scores = []
        
        # calculate distances between zipcodes
        if data['Zip Code'] != "Unsure":
            geocoding_api_key = os.environ['OpenWeather_API_KEY']
            
            shelters_coordinates = shelters.apply(lambda row: get_coordinates(row['Zip Code'], geocoding_api_key), axis=1).tolist()
            user_coordinates = get_coordinates(data['Zip Code'], geocoding_api_key)
        
            distances = []
            for coordinates in shelters_coordinates:
                 distances.append(haversine(coordinates[0], coordinates[1], user_coordinates[0], user_coordinates[1]))
        
            max = max(distances) if (max(distances) != 0) else 1
            shelters['zipcode_score'] = [d / max for d in distances]
            scores.append('zipcode_score')
    
        # get urgency scores 
        urgency_scores = shelters.apply(lambda row: get_urgency_score(data['Urgency'], row['Urgency']), axis=1).tolist()
        shelters['urgency_score'] = urgency_scores
        scores.append('urgency_score')
    
        # get duration scores
        duration_scores = shelters.apply(lambda row: get_duration_score(data['Duration'], row['Duration']), axis=1).tolist()
        shelters['duration_score'] = duration_scores
        scores.append('duration_score')
    
        # get services scores
        if data['Needs'] != "":     
            OpenAI_API_KEY = os.environ["OPENAI_API_KEY"]
            
            services_scores = shelters.apply(lambda row: call_gpt(data['Needs'], row['Services'], OpenAI_API_KEY), axis=1).tolist()
            services_scores = [s / 10 for s in services_scores]
            
            shelters['services_score'] = services_scores
            scores.append('services_score')

        # get time-based scores
        time_scores = shelters.apply(lambda row: get_time_score(datetime.now(timezone), row), axis=1).tolist()
        
        if data['Urgency'] == "Today": 
            for i in range(len(scores)):
                shelters[f'time_score_{i}'] = time_scores
                scores.append(f'time_score_{i}')
        elif data['Urgency'] == "In the next few days":
            shelters['time_score'] = time_scores
            scores.append('time_score')
        elif data['Urgency'] == "In a week or more":
            pass
            
        # calcualte cumulative score
        shelters['total_score'] = shelters[scores].sum(axis=1)
        shelters['total_score'] = shelters['total_score'] / len(scores)
    
        shelters = shelters.sort_values(by='total_score', ascending=True)
        shelters = shelters.head(3)

        # convert pandas df into list of dicts
        shelters = shelters.to_dict(orient='records')

        # text messaging
        if len(data['Phone Number']) == 12 and data['Consent']:
            try:
                account_sid = os.environ["SID"]
                auth_token = os.environ["auth_token"]
                client = Client(account_sid, auth_token)
    
                message_body = "Here's some key shelter information from using ShelterSearch today:\n\n"
                for i in range(len(shelters)):
                    phone = str(shelters[i]['Phone'])
                    message_body += f"{shelters[i]['Organization Name']}: {shelters[i]['Program Name']}\n"
                    message_body += f"🕒 Open Hours: {shelters[i]['Open Hours']}\n"
                    message_body += f"📍 Address: {shelters[i]['Address']}\n"
                    message_body += f"📞 Phone Number: ({phone[1:4]}) {phone[4:7]}-{phone[7:]}\n\n"
            
                message = client.messages.create(
                    body = message_body,
                    from_= "+15107212356",
                    to = data['Phone Number']
                ) 
            except: pass

        st.session_state.shelters_filtered = True
        st.session_state.shelters = shelters

    # Display the current shelter information
    shelter = st.session_state.shelters[st.session_state.shelter_index]
    
    st.header(f"{shelter['Organization Name']}: {shelter['Program Name']}")
    st.subheader(f"{shelter['Type']}")
    st.divider()

    st.subheader("Shelter Summary")
    st.write(shelter['Summary'])
    st.divider()

    st.subheader("How to Receive Help")
    st.write(shelter['Application Details'])
    st.markdown(f"- **🕒\tOpen Hours**: {shelter['Open Hours']}")
    st.markdown(f"- **📍\tAddress**: {shelter['Address']}")
    
    phone_number = str(shelter['Phone'])
    formatted_phone_number = f"({phone_number[1:4]}) {phone_number[4:7]}-{phone_number[7:]}"
    phone_link = f"<a href='tel:{phone_number}'>{formatted_phone_number}</a>"
    st.markdown(f"- **📞\tPhone Number**: {phone_link}", unsafe_allow_html=True)
    st.divider()

    with st.expander("More Information"):
        tabs = st.tabs(["Full List of Services", "More About the Program", "More About the Organization", "Webpage Link"])

        with tabs[0]:
            st.write(shelter['Services'])
        
        with tabs[1]:
            st.write(shelter['Program About'])
    
        with tabs[2]:
            st.write(shelter['Organization About'])
    
        with tabs[3]:
            st.write(shelter['Webpage'])
    st.divider()

    # Create map for address
    map = create_map()
    
    key = os.environ['GoogleAPI']
    address = f"{shelter['Address']}, {shelter['City']}, CA"
    lat, long = geocode_address(address, key)
    
    # Fit the map bounds to include all markers
    south_west = [lat - 0.02, long - 0.02]
    north_east = [lat + 0.02, long + 0.02]
    map_bounds = [south_west, north_east]
    map.fit_bounds(map_bounds)
    
    folium.Marker([lat, long], popup=shelter['Address']).add_to(map)
    folium_static(map)
    st.markdown(f" ## [Get Directions](https://www.google.com/maps/dir/?api=1&origin=current+location&destination={lat},{long})")
    st.divider()
            
    # Create two columns
    col1, col2, col3 = st.columns([1,1,1])
    
    # Add buttons to each column
    with col1:
        if st.button("Previous"):
            if st.session_state.shelter_index > 0:
                st.session_state.shelter_index -= 1
                st.rerun()
    
    with col2:
        if st.button("Next"):
            if st.session_state.shelter_index < 2:
                st.session_state.shelter_index += 1
                st.rerun()

    with col3:
        if st.button("Reset"):
            st.session_state.shelter_index = 0
            st.session_state.form_submitted = False
            st.session_state.shelters_filtered = False
            st.rerun()
