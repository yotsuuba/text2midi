import streamlit as st
import pandas as pd
import numpy as np
from midiutil import MIDIFile
import base64
import re
from io import BytesIO

class TextToMIDI:
    def __init__(self, bpm=120, time_signature=(4, 4), base_pitch=64, 
                 label_silence_duration=0.5, treat_underscore_as_rest=False):
        self.bpm = bpm
        self.time_signature = time_signature
        self.base_pitch = base_pitch
        self.note_duration = 2
        self.silence_duration = 2  # Regular silence between words/clusters
        self.short_silence_duration = 0.5  # Exactly half second for rests
        self.label_silence_duration = label_silence_duration
        self.final_silence = 2
        self.treat_underscore_as_rest = treat_underscore_as_rest
        
        self.special_chars = {
            'small_kana': set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ'),
            'sokuon': set('っッ'),
            'small_katakana': set('ァィゥェォヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ')
        }
        
        self.romaji_combinations = {
            'ch', 'sh', 'ts', 'th', 'ky', 'gy', 'ny', 'hy', 'ry', 'ty',
            'kw', 'gw', 'dz', 'ts', 'ai', 'ei', 'oi', 'ui', 'au', 'ou', 'eu',
            'sui', 'hui', 'kui', 'gui', 'tsui', 'chui', 'ryu', 'kyu', 'gyu', 
            'hyu', 'nyu', 'sha', 'shi', 'shu', 'sho', 'cha', 'chi', 'chu', 
            'cho', 'tsu', 'tsa', 'tsi', 'tso'
        }

    def is_romaji(self, text):
        return bool(re.match(r'^[a-zA-Z_]+$', text))

    def is_cluster(self, text):
        # Check if text is a single "word" with multiple characters
        return len(text.strip().split()) == 1 and len(text.strip()) > 1

    def is_underscore_cluster(self, text):
        # Check if text contains underscores in a pattern like "a_b_c"
        parts = text.split('_')
        return len(parts) > 1 and all(len(p) > 0 for p in parts)

    def process_romaji(self, text):
        text = text.lower()
        processed = []
        i = 0
        
        while i < len(text):
            if text[i] == '_':
                processed.append('_')
                i += 1
                continue
            
            if i + 2 < len(text):
                three_chars = text[i:i+3]
                if three_chars in self.romaji_combinations:
                    processed.append(three_chars)
                    i += 3
                    continue
                
                if three_chars[0:2] in self.romaji_combinations:
                    if three_chars[2] in 'aiueo':
                        processed.append(three_chars)
                        i += 3
                        continue
            
            if i + 1 < len(text):
                two_chars = text[i:i+2]
                if two_chars in self.romaji_combinations:
                    processed.append(two_chars)
                    i += 2
                    continue
                
                if two_chars[0] in 'bcdfghjklmnpqrstvwxyz' and two_chars[1] in 'aiueo':
                    processed.append(two_chars)
                    i += 2
                    continue
            
            processed.append(text[i])
            i += 1
        
        return processed

    def process_text(self, text):
        if self.is_romaji(text):
            return self.process_romaji(text)
        
        chars = list(text)
        processed = []
        i = 0
        
        while i < len(chars):
            if chars[i] == '_':
                processed.append('_')
                i += 1
                continue
            
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
        
        for line in lines:
            if not line.strip():
                continue
            
            if self.is_cluster(line.strip()):
                chars = self.process_text(line.strip())
                cluster_start = current_time
                is_underscore_cluster = self.is_underscore_cluster(line.strip())
                
                for i, char in enumerate(chars):
                    if char == '_':
                        if self.treat_underscore_as_rest and is_underscore_cluster:
                            # Add exactly 0.5 second rest between notes
                            current_time += 0.5  # Half second rest
                        continue
                    
                    # Add note
                    beat_time = (current_time * self.bpm) / 60
                    midi.addNote(track, 0, self.base_pitch, beat_time, 
                               (self.note_duration * self.bpm) / 60, 100)
                    current_time += self.note_duration
                    
                    # Add half second rest after note if in rest mode and not last note
                    if (self.treat_underscore_as_rest and is_underscore_cluster and 
                        i < len(chars) - 1 and chars[i + 1] == '_'):
                        current_time += 0.5  # Half second rest
                
                # Add label for the entire cluster
                label_start = max(0, cluster_start - self.label_silence_duration)
                label_end = current_time + self.label_silence_duration
                
                if labels:
                    label_start = max(label_start, labels[-1]['end'])
                
                labels.append({
                    'start': label_start,
                    'end': label_end,
                    'text': line.strip()
                })
                
                current_time += self.silence_duration
            else:
                # Handle non-cluster text (regular words)
                words = line.strip().split()
                for word in words:
                    note_start = current_time
                    
                    for char in self.process_text(word):
                        if char == '_':
                            if self.treat_underscore_as_rest:
                                current_time += 0.5  # Half second rest for non-clusters too
                            continue
                        
                        beat_time = (current_time * self.bpm) / 60
                        midi.addNote(track, 0, self.base_pitch, beat_time,
                                   (self.note_duration * self.bpm) / 60, 100)
                        current_time += self.note_duration
                    
                    label_start = max(0, note_start - self.label_silence_duration)
                    label_end = current_time + self.label_silence_duration
                    
                    if labels:
                        label_start = max(label_start, labels[-1]['end'])
                    
                    labels.append({
                        'start': label_start,
                        'end': label_end,
                        'text': word
                    })
                    
                    current_time += self.silence_duration

        total_duration = current_time + self.final_silence
        return midi, labels, total_duration

def get_note_name(midi_number):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note = notes[midi_number % 12]
    octave = (midi_number // 12) - 1
    return f"{note}{octave}"

@st.cache_data
def create_download_link(file_data, file_name, file_type):
    b64 = base64.b64encode(file_data).decode()
    return f'<a href="data:file/{file_type};base64,{b64}" download="{file_name}">Download {file_type.upper()}</a>'

def main():
    st.set_page_config(page_title="Text to MIDI Generator", layout="wide")

    st.title("Text to MIDI Generator")
    st.markdown("""
    This application generates MIDI files from text input (romaji/hiragana/katakana/english) with customizable parameters.
    Intended to be used for Vsynth Development [UTAU/DIFFSINGER/ETC].

    **Underscore Handling in Clusters**: 
    - Normal clusters (e.g., うういおあおい): Notes played continuously
    - With rest mode ON (e.g., う_う_い_お_あ_お_い): 0.5 second rests between notes
    - With rest mode OFF: Underscores ignored, notes played continuously
    """)

    with st.sidebar:
        st.header("Settings")
        bpm = st.number_input("BPM", min_value=1, max_value=300, value=120)
        time_sig_num = st.number_input("Time Signature Numerator", min_value=1, max_value=16, value=4)
        time_sig_den = st.number_input("Time Signature Denominator", min_value=1, max_value=16, value=4)
        base_pitch = st.slider("Base Pitch", min_value=21, max_value=108, value=64, 
                              help=f"Current note: {get_note_name(64)}")
        st.text(f"Selected note: {get_note_name(base_pitch)}")
        
        treat_underscore_as_rest = st.checkbox(
            "Treat '_' as Rest", 
            value=False, 
            help="When checked, '_' creates 0.5 second rests between notes"
        )
        
        create_labels = st.checkbox("Generate Label File", value=True)

    text_input = st.text_area("Enter your text:", height=200,
                             help="Enter text in hiragana, katakana, romaji, or english. For clusters with rests, use format: う_う_い_お_あ_お_い")

    if st.button("Generate MIDI"):
        if text_input:
            try:
                midi_generator = TextToMIDI(
                    bpm=bpm, 
                    time_signature=(time_sig_num, time_sig_den),
                    base_pitch=base_pitch,
                    label_silence_duration=0.5,
                    treat_underscore_as_rest=treat_underscore_as_rest
                )
                
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

if __name__ == "__main__":
    main()
