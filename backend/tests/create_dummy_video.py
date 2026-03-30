import ffmpeg

def create_video():
    print("Generating 5-second test video with silent audio...")
    audio = ffmpeg.input('anullsrc=r=44100:cl=stereo:d=5', f='lavfi')
    video = ffmpeg.input('color=c=black:s=640x480:d=5', f='lavfi')

    (
        ffmpeg
        .output(audio, video, 'test_video.mp4', vcodec='libx264', acodec='aac')
        .overwrite_output()
        .run()
    )
    print("test_video.mp4 generated.")

if __name__ == "__main__":
    create_video()
