import streamlit as st
import pandas as pd
import numpy as np
from midiutil import MIDIFile
import pretty_midi
import os
import base64
import re
from io import BytesIO

class TextToMIDI:
    def __init__(self, bpm=120, time_signature=(4, 4), base_pitch=64, label_silence_duration=0.5):
        self.bpm = bpm
        self.time_signature = time_signature
        self.base_pitch = base_pitch
        self.note_duration = 2
        self.silence_duration = 2
        self.label_silence_duration = label_silence_duration
        self.final_silence = 2  # 2 seconds of silence at the end
        
        self.special_chars = {
            'small_kana': set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ'),
            'sokuon': set('っッ'),
            'small_katakana': set('ァィゥェォヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ')
        }
        
        # Romaji combinations that should be treated as single sounds
        self.romaji_combinations = {
            'ch', 'sh', 'ts', 'th',  # Basic combinations
            'ky', 'gy', 'ny', 'hy', 'ry', 'ty',  # y-combinations
            'kw', 'gw',  # w-combinations
            'dz', 'ts',  # Other combinations
        }

    def calculate_max_label_silence(self, text):
        """Calculate maximum allowed label silence based on note spacing"""
        lines = text.strip().split('\n')
        min_gap = float('inf')
        
        current_time = self.silence_duration
        for line in lines:
            if not line.strip():
                continue
                
            is_cluster = len(line.strip().split()) == 1 and len(line.strip()) > 1
            if is_cluster:
                chars = self.process_text(line.strip())
                cluster_duration = len(chars) * self.note_duration
                min_gap = min(min_gap, self.silence_duration)
                current_time += cluster_duration + self.silence_duration
            else:
                words = line.strip().split()
                for word in words:
                    min_gap = min(min_gap, self.silence_duration)
                    current_time += self.note_duration + self.silence_duration
        
        return min_gap / 2

    def is_romaji(self, text):
        """Check if text is likely romaji"""
        return bool(re.match(r'^[a-zA-Z]+$', text))

    def process_romaji(self, text):
        """Process romaji text into phonetic units"""
        text = text.lower()
        processed = []
        i = 0
        
        while i < len(text):
            # Check for three-letter combinations
            if i + 2 < len(text):
                three_chars = text[i:i+3]
                if three_chars.startswith(tuple(self.romaji_combinations)):
                    processed.append(three_chars)
                    i += 3
                    continue
            
            # Check for two-letter combinations
            if i + 1 < len(text):
                two_chars = text[i:i+2]
                if two_chars in self.romaji_combinations:
                    processed.append(two_chars)
                    i += 2
                    continue
            
            # Single character
            processed.append(text[i])
            i += 1
        
        return processed

    def process_text(self, text):
        """Process text handling both romaji and kana"""
        if self.is_romaji(text):
            return self.process_romaji(text)
        
        # Original kana processing
        chars = list(text)
        processed = []
        i = 0
        
        while i < len(chars):
            current_char = chars[i]
            combined_char = current_char
            
            if i < len(chars) - 1:
                next_char = chars[i + 1]
                
                if next_char in self.special_chars['small_kana']:
                    combined_char = current_char + next_char
                    i += 2
                elif current_char in self.special_chars['sokuon']:
                    if i < len(chars) - 2 and chars[i + 2] in self.special_chars['small_kana']:
                        combined_char = chars[i + 1] + chars[i + 2]
                        i += 3
                    else:
                        combined_char = chars[i + 1]
                        i += 2
                elif next_char in self.special_chars['small_katakana']:
                    combined_char = current_char + next_char
                    i += 2
                else:
                    i += 1
                    
                processed.append(combined_char)
                continue
            
            processed.append(current_char)
            i += 1
                
        return processed

    def create_midi(self, text):
        midi = MIDIFile(1)
        track = 0
        time = 0
        
        midi.addTempo(track, time, self.bpm)
        midi.addTimeSignature(track, time, *self.time_signature, 24, 8)
        
        lines = text.strip().split('\n')
        current_time = self.silence_duration
        labels = []
        last_note_end = 0
        
        for line in lines:
            if not line.strip():
                continue
                
            is_cluster = len(line.strip().split()) == 1 and len(line.strip()) > 1
            
            if is_cluster:
                chars = self.process_text(line.strip())
                cluster_start = current_time
                
                for char in chars:
                    beat_time = (current_time * self.bpm) / 60
                    midi.addNote(track, 0, self.base_pitch, beat_time, 
                               (self.note_duration * self.bpm) / 60, 100)
                    current_time += self.note_duration
                
                label_start = max(0, cluster_start - self.label_silence_duration)
                label_end = current_time + self.label_silence_duration
                
                if labels:
                    label_start = max(label_start, labels[-1]['end'])
                
                labels.append({
                    'start': label_start,
                    'end': label_end,
                    'text': line.strip()
                })
                
                last_note_end = current_time
                current_time += self.silence_duration
            else:
                words = line.strip().split()
                for word in words:
                    processed_word = ''.join(self.process_text(word))
                    note_start = current_time
                    
                    beat_time = (current_time * self.bpm) / 60
                    midi.addNote(track, 0, self.base_pitch, beat_time,
                               (self.note_duration * self.bpm) / 60, 100)
                    
                    label_start = max(0, note_start - self.label_silence_duration)
                    label_end = current_time + self.note_duration + self.label_silence_duration
                    
                    if labels:
                        label_start = max(label_start, labels[-1]['end'])
                    
                    labels.append({
                        'start': label_start,
                        'end': label_end,
                        'text': processed_word
                    })
                    
                    last_note_end = current_time + self.note_duration
                    current_time += self.note_duration + self.silence_duration

        current_time += self.final_silence
        
        return midi, labels, last_note_end + self.final_silence

def get_note_name(midi_number):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note = notes[midi_number % 12]
    octave = (midi_number // 12) - 1
    return f"{note}{octave}"

@st.cache_data
def create_download_link(file_data, file_name, file_type):
    """Create a download link for file data."""
    b64 = base64.b64encode(file_data).decode()
    return f'<a href="data:file/{file_type};base64,{b64}" download="{file_name}">Download {file_type.upper()}</a>'

st.set_page_config(page_title="Text to MIDI Generator", layout="wide")

st.title("Text to MIDI Generator")
st.markdown("""
This application generates MIDI files from text input (romaji/hiragana/katakana/english) with customizable parameters.
Intended to be used for Vsynth Development [UTAU/DIFFSINGER/ETC].
""")

with st.sidebar:
    st.header("Settings")
    bpm = st.number_input("BPM", min_value=1, max_value=300, value=120)
    time_sig_num = st.number_input("Time Signature Numerator", min_value=1, max_value=16, value=4)
    time_sig_den = st.number_input("Time Signature Denominator", min_value=1, max_value=16, value=4)
    base_pitch = st.slider("Base Pitch", min_value=21, max_value=108, value=64, 
                          help=f"Current note: {get_note_name(64)}")
    st.text(f"Selected note: {get_note_name(base_pitch)}")
    create_labels = st.checkbox("Generate Label File", value=True)

text_input = st.text_area("Enter your text:", height=200,
                         help="Enter text in hiragana, katakana, romaji, or english. Use empty lines to separate clusters.")

if text_input:
    temp_midi = TextToMIDI(bpm=bpm, time_signature=(time_sig_num, time_sig_den))
    max_silence = temp_midi.calculate_max_label_silence(text_input)
    
    label_silence = st.slider(
        "Label Silence Duration (seconds)", 
        min_value=0.1, 
        max_value=float(max_silence), 
        value=min(0.5, max_silence),
        step=0.1,
        help="Maximum value is calculated to prevent label overlap"
    )
else:
    label_silence = 0.5

if st.button("Generate MIDI"):
    if text_input:
        midi_generator = TextToMIDI(
            bpm=bpm, 
            time_signature=(time_sig_num, time_sig_den),
            base_pitch=base_pitch,
            label_silence_duration=label_silence
        )
        
        try:
            midi_data, labels, total_duration = midi_generator.create_midi(text_input)
            
            midi_buffer = BytesIO()
            midi_data.writeFile(midi_buffer)
            midi_bytes = midi_buffer.getvalue()
            
            if create_labels:
                label_content = '\n'.join([
                    f"{label['start']:.3f}\t{label['end']:.3f}\t{label['text']}" 
                    for label in labels
                ]).encode('utf-8')
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(create_download_link(midi_bytes, "output.mid", "midi"), unsafe_allow_html=True)
            if create_labels:
                with col2:
                    st.markdown(create_download_link(label_content, "labels.txt", "text"), unsafe_allow_html=True)
            
            st.info(f"Total duration: {total_duration:.2f} seconds")
            
            if create_labels:
                st.subheader("Label Preview")
                df = pd.DataFrame(labels)
                st.dataframe(df)
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter some text first.")
    
    st.markdown("""
    ---
    *Made by H5X2 with love, 2024-2025*.
    """)
