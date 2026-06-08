import io
from pydub import AudioSegment

final = AudioSegment.empty()
silence = AudioSegment.silent(duration=1000)

final += silence
final.export("test_out.mp3", format="mp3")
print("Exported")
