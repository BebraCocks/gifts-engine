"""Optional local dictation check. Downloads its own model on first use; CPU by default."""
import argparse

MODELS = {'small': 'Systran/faster-whisper-small', 'medium': 'Systran/faster-whisper-medium',
          'large-v3': 'Systran/faster-whisper-large-v3'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    parser.add_argument('--model', choices=MODELS, default='small')
    args = parser.parse_args()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit('Install requirements-optional.txt first') from None
    model = WhisperModel(MODELS[args.model], device='cpu', compute_type='int8')
    for file in args.files:
        segments, _ = model.transcribe(file, language='ru', beam_size=5, initial_prompt=None,
                                       condition_on_previous_text=False)
        print(file, ' '.join(segment.text.strip() for segment in segments))
    print('Machine transcription is a supporting check; listen to the actual takes as well.')


if __name__ == '__main__':
    main()
