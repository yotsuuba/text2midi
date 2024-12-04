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
        self.rest_duration = 0.5  # Exactly half second for rests
        self.label_silence_duration = label_silence_duration
        self.final_silence = 2
        self.treat_underscore_as_rest = treat_underscore_as_rest
        
        # [Special chars and romaji combinations remain the same]
        
    # [Previous methods remain the same until create_midi]

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
                
                # Track the end time of the last note in the cluster
                last_note_end = cluster_start
                
                for i, char in enumerate(chars):
                    if char == '_':
                        if self.treat_underscore_as_rest and is_underscore_cluster:
                            current_time += self.rest_duration
                        continue
                    
                    # Add note
                    beat_time = (current_time * self.bpm) / 60
                    midi.addNote(track, 0, self.base_pitch, beat_time, 
                               (self.note_duration * self.bpm) / 60, 100)
                    current_time += self.note_duration
                    last_note_end = current_time
                    
                    # Add rest after note if in rest mode and not last note
                    if (self.treat_underscore_as_rest and is_underscore_cluster and 
                        i < len(chars) - 1 and chars[i + 1] == '_'):
                        current_time += self.rest_duration
                
                # Calculate label timing based on rest mode
                label_start = max(0, cluster_start - self.label_silence_duration)
                if self.treat_underscore_as_rest and is_underscore_cluster:
                    # Include the final rest duration in the label end time
                    label_end = current_time + self.label_silence_duration
                else:
                    # Use the last note end time for label end when rest mode is off
                    label_end = last_note_end + self.label_silence_duration
                
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
                    last_note_end = note_start
                    
                    for char in self.process_text(word):
                        if char == '_':
                            if self.treat_underscore_as_rest:
                                current_time += self.rest_duration
                            continue
                        
                        beat_time = (current_time * self.bpm) / 60
                        midi.addNote(track, 0, self.base_pitch, beat_time,
                                   (self.note_duration * self.bpm) / 60, 100)
                        current_time += self.note_duration
                        last_note_end = current_time
                    
                    # Calculate label timing based on rest mode
                    label_start = max(0, note_start - self.label_silence_duration)
                    if self.treat_underscore_as_rest and '_' in word:
                        label_end = current_time + self.label_silence_duration
                    else:
                        label_end = last_note_end + self.label_silence_duration
                    
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

# [Rest of the code remains the same]
