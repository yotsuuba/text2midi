# Text to MIDI Generator

A Streamlit-based web application that converts Japanese text (romaji/hiragana/katakana) into MIDI files with customizable parameters. Perfect for UTAU/DIFFSINGER and other voice synthesis development workflows.

https://text2midi.streamlit.app/ Live demo 

## Features

- Convert text to MIDI with customizable parameters
- Support for Japanese text input (romaji/hiragana/katakana)
- Special character handling (sokuon っ/ッ and small kana)
- Adjustable BPM and time signature
- Customizable base pitch
- Label file generation for voice synthesis timing
- Real-time label preview
- Automatic silence duration calculation
- Clean and intuitive user interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yotsuuba/text2midi.git
cd text2midi
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

- streamlit
- pandas
- numpy
- midiutil
- jaconv
- pretty_midi

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to `http://localhost:8501`

3. Configure the settings in the sidebar:
   - BPM (1-300)
   - Time Signature
   - Base Pitch (21-108)
   - Label File Generation

4. Enter your text in the main text area
   - Supports hiragana, katakana, or romaji
   - Use empty lines to separate clusters

5. Adjust the Label Silence Duration if needed

6. Click "Generate MIDI" to create your files

## Input Format

The application accepts text in the following formats:
- Hiragana: あいうえお
- Katakana: アイウエオ
- Romaji: aiueo

Use empty lines to separate clusters for proper timing:

```
こんにちは
世界
```

## Output Files

1. MIDI File (.mid):
   - Contains the generated musical notes
   - Uses specified BPM and time signature
   - Each character/syllable becomes a note

2. Label File (.txt) [Optional]:
   - Contains timing information
   - Format: `start_time end_time text`
   - Useful for voice synthesis timing

## Configuration Options

| Parameter | Range | Description |
|-----------|-------|-------------|
| BPM | 1-300 | Tempo in beats per minute |
| Time Signature | 1-16/1-16 | Musical time signature |
| Base Pitch | 21-108 | MIDI note number (C0-C8) |
| Label Silence | 0.1-max | Silence duration between labels |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Credits

Created by H5X2 (2024-2025)

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Acknowledgments

- Thanks to the Streamlit team for the amazing framework
- All contributors and users of this tool
