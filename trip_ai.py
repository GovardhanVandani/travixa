import openai
from dotenv import load_dotenv
import os
import requests
from models import Trip, ItineraryItem, Participant
import json

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

class TripAI:
    def __init__(self):
        self.unsplash_url = "https://source.unsplash.com/400x250"
    
    def generate_smart_itinerary(self, trip_id):
        """Generate AI itinerary from participant survey data"""
        trip = Trip.query.get(trip_id)
        participants = Participant.query.filter_by(trip_id=trip_id).all()
        
        # Aggregate preferences
        prefs_summary = self._analyze_preferences(participants)
        
        prompt = f"""
Generate a {trip.days}-day itinerary for {trip.destination}:

TRIP DETAILS:
- Budget: ${trip.budget} total ({len(participants)} people)
- Preferences: {prefs_summary}
- Duration: {trip.start_date} to {trip.end_date}

FORMAT (JSON array):
[
  {{
    "day": 1,
    "time": "09:00",
    "place": "Place Name",
    "description": "2-3 sentences",
    "duration": "3 hours",
    "cost": 25.50,
    "category": "sightseeing"
  }}
]

Return ONLY valid JSON.
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            
            itinerary = json.loads(response.choices[0].message.content)
            self._save_enhanced_itinerary(trip, itinerary)
            
        except Exception as e:
            self._fallback_itinerary(trip)
    
    def _analyze_preferences(self, participants):
        """Convert survey responses to summary"""
        summary = []
        for p in participants:
            if p.survey_responses:
                responses = json.loads(p.survey_responses)
                prefs = self._decode_responses(responses)
                summary.append(f"{p.name}: {prefs}")
        return "; ".join(summary)
    
    def _decode_responses(self, responses):
        prefs = {
            1: "Adventure", 2: "Relaxation", 3: "Culture", 4: "Food",
            5: "Low Budget", 6: "Medium", 7: "High",
            8: "Fast Pace", 9: "Moderate", 10: "Slow",
            11: "History", 12: "Nature", 13: "Shopping"
        }
        return ", ".join([prefs.get(r, "Other") for r in responses])
    
    def _save_enhanced_itinerary(self, trip, itinerary_data):
        """Save AI itinerary with images"""
        for i, item in enumerate(itinerary_data):
            img_url = f"{self.unsplash_url}/?{item['place']}+{trip.destination}"
            
            itinerary_item = ItineraryItem(
                trip_id=trip.id,
                day=item.get('day', 1),
                time=item.get('time', '09:00'),
                place_name=item['place'],
                description=item['description'],
                image_url=img_url,
                duration=item['duration'],
                cost_estimate=item['cost'],
                category=item.get('category', 'general')
            )
        db.session.commit()
    
    def _fallback_itinerary(self, trip):
        """Smart fallback if AI fails"""
        # Create sensible default itinerary
        pass