from twilio.rest import Client
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import json

load_dotenv()

db = SQLAlchemy()

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20), unique=True)
    trip_id = db.Column(db.Integer)
    survey_step = db.Column(db.Integer, default=1)
    survey_responses = db.Column(db.Text, default='[]')

class SMSSurvey:
    def __init__(self):
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    
    def start_survey(self, participant):
        """Send first survey question"""
        questions = [
            "Q1: Trip type? 1=Adventure 2=Relax 3=Culture 4=Food",
            "Q2: Budget? 1=Low 2=Medium 3=High", 
            "Q3: Pace? 1=Fast 2=Moderate 3=Slow",
            "Q4: Interests? 1=History 2=Nature 3=Shopping 4=None"
        ]
        
        msg = f"Hi {participant.name}! Travixa Trip Survey\n\n{questions[0]}\nReply 1-4 only"
        
        self.client.messages.create(
            body=msg,
            from_=self.twilio_phone,
            to=participant.phone
        )
        return True
    
    def process_reply(self, phone, reply):
        """Handle survey response"""
        participant = Participant.query.filter_by(phone=phone).first()
        if not participant:
            return "Participant not found"
        
        try:
            answer = int(reply.strip())
            if 1 <= answer <= 4:
                responses = json.loads(participant.survey_responses or '[]')
                responses.append(answer)
                participant.survey_responses = json.dumps(responses)
                participant.survey_step += 1
                
                db.session.commit()
                
                if participant.survey_step > 4:
                    self.send_completion(participant)
                    return "Survey complete!"
                else:
                    self.send_next_question(participant)
                    return f"Step {participant.survey_step} complete"
            else:
                return "Invalid. Reply 1-4 only"
        except:
            return "Invalid response. Reply 1-4"
    
    def send_next_question(self, participant):
        questions = [
            "Q2: Budget? 1=Low 2=Medium 3=High",
            "Q3: Pace? 1=Fast 2=Moderate 3=Slow",
            "Q4: Interests? 1=History 2=Nature 3=Shopping 4=None"
        ]
        msg = f"{questions[participant.survey_step-2]}\nReply 1-4 only"
        
        self.client.messages.create(
            body=msg,
            from_=self.twilio_phone,
            to=participant.phone
        )
    
    def send_completion(self, participant):
        msg = f"""✅ {participant.name}, survey complete!

AI trip plan coming soon based on your preferences!

Track progress: travixa.com"""
        
        self.client.messages.create(
            body=msg,
            from_=self.twilio_phone,
            to=participant.phone
        )