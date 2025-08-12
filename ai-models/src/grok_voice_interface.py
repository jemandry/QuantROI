#!/usr/bin/env python3
"""
Grok-Style Voice/Video UX for Interactive Compliance
Implements voice and video interfaces for compliance simulations and tutorials
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum

try:
    import speech_recognition as sr
    import pyttsx3
    SPEECH_LIBRARIES_AVAILABLE = True
except ImportError:
    SPEECH_LIBRARIES_AVAILABLE = False
    logging.warning("Speech libraries not available - using text-only interface")

try:
    import cv2
    import numpy as np
    VIDEO_LIBRARIES_AVAILABLE = True
except ImportError:
    VIDEO_LIBRARIES_AVAILABLE = False
    logging.warning("Video libraries not available - using audio-only interface")

class InteractionMode(Enum):
    TEXT_ONLY = "text_only"
    VOICE_ONLY = "voice_only"
    VIDEO_VOICE = "video_voice"
    FULL_INTERACTIVE = "full_interactive"

class ComplianceSimulationType(Enum):
    CYBER_DISCLOSURE = "cyber_disclosure"
    SEC_FILING = "sec_filing"
    RISK_ASSESSMENT = "risk_assessment"
    REGULATORY_TRAINING = "regulatory_training"

@dataclass
class VoiceCommand:
    command_id: str
    text: str
    confidence: float
    intent: str
    parameters: Dict[str, Any]
    timestamp: str

@dataclass
class ComplianceSimulation:
    simulation_id: str
    simulation_type: ComplianceSimulationType
    scenario_description: str
    learning_objectives: List[str]
    interactive_steps: List[Dict[str, Any]]
    completion_criteria: Dict[str, Any]
    estimated_duration_minutes: int

class GrokVoiceInterface:
    """Grok-style voice interface for compliance interactions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.interaction_mode = InteractionMode(config.get('interaction_mode', 'text_only'))
        
        self.recognizer = None
        self.tts_engine = None
        self.microphone = None
        
        if SPEECH_LIBRARIES_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.tts_engine = pyttsx3.init()
            
            voices = self.tts_engine.getProperty('voices')
            if voices:
                self.tts_engine.setProperty('voice', voices[0].id)
            self.tts_engine.setProperty('rate', 150)  # Speaking rate
            self.tts_engine.setProperty('volume', 0.8)  # Volume level
        
        self.video_capture = None
        if VIDEO_LIBRARIES_AVAILABLE and self.interaction_mode in [InteractionMode.VIDEO_VOICE, InteractionMode.FULL_INTERACTIVE]:
            try:
                self.video_capture = cv2.VideoCapture(0)
            except Exception as e:
                self.logger.warning(f"Video capture initialization failed: {e}")
        
        self.conversation_history = []
        self.current_simulation = None
        self.user_progress = {}
        
        self.intent_patterns = {
            'start_simulation': ['start', 'begin', 'initiate', 'launch'],
            'explain_concept': ['explain', 'what is', 'define', 'clarify'],
            'next_step': ['next', 'continue', 'proceed', 'forward'],
            'repeat': ['repeat', 'again', 'say that again'],
            'help': ['help', 'assistance', 'guide', 'support'],
            'exit': ['exit', 'quit', 'stop', 'end']
        }
    
    async def start_interactive_session(self) -> bool:
        """Start interactive compliance session"""
        try:
            await self._speak("Welcome to the Grok-style Compliance AI Assistant. How can I help you today?")
            
            if self.interaction_mode == InteractionMode.TEXT_ONLY:
                return await self._text_interaction_loop()
            else:
                return await self._voice_interaction_loop()
                
        except Exception as e:
            self.logger.error(f"Error starting interactive session: {e}")
            return False
    
    async def _voice_interaction_loop(self):
        """Main voice interaction loop"""
        if not SPEECH_LIBRARIES_AVAILABLE:
            self.logger.warning("Speech libraries not available - falling back to text")
            return await self._text_interaction_loop()
        
        session_active = True
        
        while session_active:
            try:
                command = await self._listen_for_command()
                
                if command:
                    self.conversation_history.append({
                        'type': 'user_voice',
                        'content': command.text,
                        'confidence': command.confidence,
                        'timestamp': command.timestamp
                    })
                    
                    response = await self._process_voice_command(command)
                    
                    if response:
                        await self._speak(response)
                        
                        self.conversation_history.append({
                            'type': 'assistant_voice',
                            'content': response,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    if command.intent == 'exit':
                        session_active = False
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                await self._speak("Session ended by user. Goodbye!")
                session_active = False
            except Exception as e:
                self.logger.error(f"Error in voice interaction loop: {e}")
                await self._speak("I encountered an error. Please try again.")
        
        return True
    
    async def _text_interaction_loop(self):
        """Fallback text interaction loop"""
        session_active = True
        
        print("Grok Compliance AI Assistant (Text Mode)")
        print("Type 'exit' to end the session")
        
        while session_active:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Assistant: Goodbye! Stay compliant!")
                    session_active = False
                    continue
                
                command = VoiceCommand(
                    command_id=f"text_cmd_{int(datetime.now().timestamp())}",
                    text=user_input,
                    confidence=1.0,
                    intent=self._classify_intent(user_input),
                    parameters={},
                    timestamp=datetime.now().isoformat()
                )
                
                response = await self._process_voice_command(command)
                
                if response:
                    print(f"Assistant: {response}")
                
            except KeyboardInterrupt:
                print("\nAssistant: Session ended. Goodbye!")
                session_active = False
            except Exception as e:
                self.logger.error(f"Error in text interaction: {e}")
                print("Assistant: I encountered an error. Please try again.")
        
        return True
    
    async def _listen_for_command(self) -> Optional[VoiceCommand]:
        """Listen for voice command"""
        if not self.recognizer or not self.microphone:
            return None
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            text = self.recognizer.recognize_google(audio)
            confidence = 0.8  # Google API doesn't provide confidence scores
            
            command = VoiceCommand(
                command_id=f"voice_cmd_{int(datetime.now().timestamp())}",
                text=text,
                confidence=confidence,
                intent=self._classify_intent(text),
                parameters=self._extract_parameters(text),
                timestamp=datetime.now().isoformat()
            )
            
            print(f"Recognized: {text} (confidence: {confidence:.2f})")
            return command
            
        except sr.WaitTimeoutError:
            print("No speech detected")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None
    
    def _classify_intent(self, text: str) -> str:
        """Classify user intent from text"""
        text_lower = text.lower()
        
        for intent, patterns in self.intent_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return intent
        
        return 'general_query'
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract parameters from text"""
        parameters = {}
        text_lower = text.lower()
        
        if 'cyber' in text_lower or 'security' in text_lower:
            parameters['simulation_type'] = ComplianceSimulationType.CYBER_DISCLOSURE.value
        elif 'filing' in text_lower or 'sec' in text_lower:
            parameters['simulation_type'] = ComplianceSimulationType.SEC_FILING.value
        elif 'risk' in text_lower:
            parameters['simulation_type'] = ComplianceSimulationType.RISK_ASSESSMENT.value
        elif 'training' in text_lower:
            parameters['simulation_type'] = ComplianceSimulationType.REGULATORY_TRAINING.value
        
        return parameters
    
    async def _process_voice_command(self, command: VoiceCommand) -> Optional[str]:
        """Process voice command and generate response"""
        try:
            if command.intent == 'start_simulation':
                return await self._handle_start_simulation(command)
            elif command.intent == 'explain_concept':
                return await self._handle_explain_concept(command)
            elif command.intent == 'next_step':
                return await self._handle_next_step(command)
            elif command.intent == 'repeat':
                return await self._handle_repeat_request(command)
            elif command.intent == 'help':
                return await self._handle_help_request(command)
            elif command.intent == 'exit':
                return "Thank you for using the Compliance AI Assistant. Goodbye!"
            else:
                return await self._handle_general_query(command)
                
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            return "I'm sorry, I encountered an error processing your request. Please try again."
    
    async def _handle_start_simulation(self, command: VoiceCommand) -> str:
        """Handle simulation start request"""
        simulation_type = command.parameters.get('simulation_type')
        
        if not simulation_type:
            return "What type of compliance simulation would you like to start? I can help with cyber disclosure, SEC filing, risk assessment, or regulatory training."
        
        simulation = self._create_simulation(ComplianceSimulationType(simulation_type))
        self.current_simulation = simulation
        
        return f"Starting {simulation.simulation_type.value} simulation. {simulation.scenario_description} Are you ready to begin?"
    
    async def _handle_explain_concept(self, command: VoiceCommand) -> str:
        """Handle concept explanation request"""
        text_lower = command.text.lower()
        
        if 'cyber disclosure' in text_lower:
            return "Cyber disclosure refers to the SEC requirement for public companies to disclose material cybersecurity incidents within 4 business days. This includes incidents that could reasonably be expected to materially impact the company."
        elif 'materiality' in text_lower:
            return "Materiality in compliance refers to information that would be important to a reasonable investor's decision-making process. It's not just about financial impact, but also reputational and operational effects."
        elif 'sec filing' in text_lower:
            return "SEC filings are mandatory reports that public companies must submit to the Securities and Exchange Commission. Key filings include 10-K annual reports, 10-Q quarterly reports, and 8-K current reports for material events."
        else:
            return "I can explain various compliance concepts. Try asking about cyber disclosure, materiality, SEC filings, or other regulatory topics."
    
    async def _handle_next_step(self, command: VoiceCommand) -> str:
        """Handle next step request"""
        if not self.current_simulation:
            return "No active simulation. Would you like to start a new compliance simulation?"
        
        current_step = self.user_progress.get(self.current_simulation.simulation_id, 0)
        
        if current_step < len(self.current_simulation.interactive_steps):
            step = self.current_simulation.interactive_steps[current_step]
            self.user_progress[self.current_simulation.simulation_id] = current_step + 1
            
            return f"Step {current_step + 1}: {step['description']} {step.get('instruction', '')}"
        else:
            return "Congratulations! You've completed the simulation. Would you like to start another one?"
    
    async def _handle_repeat_request(self, command: VoiceCommand) -> str:
        """Handle repeat request"""
        if self.conversation_history:
            last_assistant_message = None
            for msg in reversed(self.conversation_history):
                if msg['type'] == 'assistant_voice':
                    last_assistant_message = msg['content']
                    break
            
            if last_assistant_message:
                return f"I said: {last_assistant_message}"
        
        return "I don't have anything to repeat. How can I help you?"
    
    async def _handle_help_request(self, command: VoiceCommand) -> str:
        """Handle help request"""
        return """I'm your Grok-style Compliance AI Assistant. I can help you with:
        
        1. Start compliance simulations - say 'start cyber disclosure simulation'
        2. Explain compliance concepts - ask 'what is materiality?'
        3. Guide you through regulatory processes
        4. Provide interactive training
        
        Just speak naturally and I'll do my best to help!"""
    
    async def _handle_general_query(self, command: VoiceCommand) -> str:
        """Handle general queries"""
        return f"I heard you say: '{command.text}'. I'm here to help with compliance matters. You can ask me to start a simulation, explain concepts, or provide guidance on regulatory topics."
    
    def _create_simulation(self, simulation_type: ComplianceSimulationType) -> ComplianceSimulation:
        """Create simulation based on type"""
        if simulation_type == ComplianceSimulationType.CYBER_DISCLOSURE:
            return ComplianceSimulation(
                simulation_id=f"sim_{int(datetime.now().timestamp())}",
                simulation_type=simulation_type,
                scenario_description="Your company has experienced a cybersecurity incident that may require SEC disclosure.",
                learning_objectives=[
                    "Understand materiality assessment for cyber incidents",
                    "Learn the 4-day disclosure timeline",
                    "Practice drafting disclosure language"
                ],
                interactive_steps=[
                    {
                        'description': 'Assess the materiality of the cyber incident',
                        'instruction': 'Consider the impact on operations, data, and reputation'
                    },
                    {
                        'description': 'Determine disclosure timeline requirements',
                        'instruction': 'Calculate the 4 business day deadline from discovery'
                    },
                    {
                        'description': 'Draft the disclosure statement',
                        'instruction': 'Include incident nature, timing, and material impact'
                    }
                ],
                completion_criteria={'steps_completed': 3, 'minimum_score': 80},
                estimated_duration_minutes=15
            )
        else:
            return ComplianceSimulation(
                simulation_id=f"sim_{int(datetime.now().timestamp())}",
                simulation_type=simulation_type,
                scenario_description="General compliance training simulation.",
                learning_objectives=["Understand basic compliance principles"],
                interactive_steps=[
                    {
                        'description': 'Review compliance fundamentals',
                        'instruction': 'Learn key regulatory concepts'
                    }
                ],
                completion_criteria={'steps_completed': 1, 'minimum_score': 70},
                estimated_duration_minutes=10
            )
    
    async def _speak(self, text: str):
        """Convert text to speech"""
        if SPEECH_LIBRARIES_AVAILABLE and self.tts_engine and self.interaction_mode != InteractionMode.TEXT_ONLY:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS error: {e}")
                print(f"Assistant: {text}")  # Fallback to text
        else:
            print(f"Assistant: {text}")
    
    async def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            'interaction_mode': self.interaction_mode.value,
            'conversation_length': len(self.conversation_history),
            'current_simulation': self.current_simulation.simulation_id if self.current_simulation else None,
            'user_progress': self.user_progress,
            'session_duration': 'active',
            'last_updated': datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.video_capture:
            self.video_capture.release()
        if VIDEO_LIBRARIES_AVAILABLE:
            cv2.destroyAllWindows()

async def test_grok_voice_interface():
    """Test the Grok voice interface"""
    config = {
        'interaction_mode': 'text_only'  # Change to 'voice_only' for voice testing
    }
    
    interface = GrokVoiceInterface(config)
    
    try:
        await interface.start_interactive_session()
    finally:
        interface.cleanup()

if __name__ == "__main__":
    asyncio.run(test_grok_voice_interface())
