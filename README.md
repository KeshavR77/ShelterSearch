## ShelterSearch

# Usage
Please visit https://keshavra-sheltersearch.hf.space/.

# Inspiration
For the last couple of years, I've been an operations/tech intern at a couple of nonprofit shelters for unhoused youth (one in SF, one in Oakland/Berkeley). I identified one large problem: lack of quality information about shelters for unhoused youth in need of help. There's a bunch of information out there, but a lot of it is inaccurate and overcomplicated, leaving unhoused youth, who often face trauma and mental health issues, confused. My app seeks to solve this issue, simplifying the process and making it easy to quickly receive help.

# What it does
When you load up the site, you are presented with a form, asking for information about you location, zipcode, identity, needs, etc. After the user submits the form, we use their information to generate the shelters the top three shelters that best fit their needs from a back-end database of around 30 shelters in San Francisco, Oakland, and Berkeley. Then the app displays information about the shelter in a culturally-relevant way: simple and to-the-point, providing a one sentence summary of the shelter's services, and quick instructions on how to receive help from the shelter. If you want, you can access additional information about that shelter and directions on how to get there. The app also texts you the information so you can access it after you're done using it.

# How we built it
The process began with a long research phase, looking at shelters across the bay and compiling accurate information from trusted sources such as government sites into a database with 20 columns and 30 rows. Then, I used streamlit and python to develop the app, beginning with the form, continuing with the logic that recommends the best shelters, and finishing with the information display. The app uses OpenAI API to match how well the user's needs fit the shelter's services, Google's Geocoding API to calculate the distance between the user and the shelter, and Twilio to send text messages. It also compares the urgency and duration of the user to the shelter.

# Challenges we ran into
One large challenge was finding the right information, as a lot of information out there is inaccurate. It was a time-consuming process. Another challenge was finding accurate APIs. My first geocoding API was inaccurate for many zipcodes, so through testing around five API's, I was able to find the best one. Twilio also proved difficult to set up, requiring an elaborate verifiction process to ensure proper and consentual text messaging procedures. Finally, it was difficulty to synthesize the abundance of information out there into a easy-to-follow guide. We really needed to capture only what was most important.

# Accomplishments that we're proud of
The app is able to take a super complicated looking csv file and condense it into only what's most relevant. I believe the app has transformative potential for unhoused youth in the Bay Area.

# What we learned
I learned how to use hugging face and streamlit applications. I learned how to conduct research with a focus on accuracy. Learned how to be sensitive and aware of the youth this app serves.

# What's next for ShelterSearch
I'm working with Youth Spirit Artworks, a nonprofit youth shelter, to deploy and test this app. I'm planning to apply for a grant to roll out this app in the cities of Oakland, San Francisco, and Berkeley.
