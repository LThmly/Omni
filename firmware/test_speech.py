"""Recognition pipeline tests: partial revisions, queued audio flush and cancel."""
import json
import time
import unittest
from speech import VoskSpeech


class Recognizer:
    def __init__(self, model, rate):
        self.chunk=None
    def AcceptWaveform(self, chunk):
        self.chunk=chunk
        return chunk==b'commit'
    def Result(self): return json.dumps({'text':'add milk'})
    def PartialResult(self):
        return json.dumps({'partial':{b'wrong':'add mill',b'correct':'add milk',b'tail':'to my'}[self.chunk]})
    def FinalResult(self): return json.dumps({'text':'to my shopping list'})


class Audio:
    def __init__(self, chunks=(), error=False, status=None):
        self.chunks=chunks;self.error=error;self.stopped=False;self.status=status
    def query_devices(self, device, kind):
        if self.error: raise RuntimeError('No input device')
        return {'name':'Test microphone','default_samplerate':16000}
    def RawInputStream(self, **kwargs):
        self.kwargs=kwargs
        return self
    def __enter__(self):
        for chunk in self.chunks:self.kwargs['callback'](chunk,1600,None,self.status)
        return self
    def stop(self):self.stopped=True
    def __exit__(self,*args):self.stop()


class SpeechTest(unittest.TestCase):
    def make(self, audio):
        speech=VoskSpeech(model=object(),audio=audio,recognizer_factory=Recognizer)
        self.addCleanup(speech.close)
        return speech

    def wait_for(self, speech, kind):
        events=[];deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            events+=speech.poll()
            if any(event[1]==kind for event in events):return events
            time.sleep(.005)
        self.fail(f'No {kind} event: {events}')

    def test_revisions_and_final_flush_keep_every_segment(self):
        audio=Audio([b'wrong',b'correct',b'commit',b'tail'])
        speech=self.make(audio);session=speech.start()
        events=self.wait_for(speech,'segment')
        speech.finish(session)
        speech.session['thread'].join(2)
        events+=speech.poll()
        self.assertFalse(speech.session['thread'].is_alive())
        self.assertEqual([data['partial'] for _,kind,data in events if kind=='partial'],['add mill','add milk','to my'])
        self.assertEqual([data['text'] for _,kind,data in events if kind=='final'],['add milk to my shopping list'])
        self.assertTrue(all(number==session for number,_,_ in events))
        self.assertTrue(audio.stopped)
        self.assertEqual(audio.kwargs['channels'],1)
        self.assertEqual(audio.kwargs['dtype'],'int16')

    def test_cancel_never_emits_a_final_request(self):
        speech=self.make(Audio())
        session=speech.start();self.wait_for(speech,'ready')
        speech.cancel(session);speech.session['thread'].join(2)
        self.assertFalse(any(kind=='final' for _,kind,_ in speech.poll()))
        second=speech.start();self.assertNotEqual(session,second)
        speech.cancel(second)

    def test_input_failure_returns_error_without_fake_transcript(self):
        speech=self.make(Audio(error=True));speech.start()
        events=self.wait_for(speech,'error')
        self.assertEqual(events[0][1],'error')
        self.assertIn('No input device',events[0][2])
        self.assertFalse(any(kind in ('final','partial') for _,kind,_ in events))

    def test_full_decode_queue_reports_error_instead_of_submitting_truncated_speech(self):
        speech=self.make(Audio([b'correct']*101));speech.start()
        events=self.wait_for(speech,'error')
        self.assertIn('audio overflow',next(data for _,kind,data in events if kind=='error'))
        self.assertFalse(any(kind=='final' for _,kind,_ in events))

    def test_transient_audio_overrun_keeps_current_audio_and_finalizes(self):
        speech=self.make(Audio([b'wrong',b'correct'],status='input overflow'))
        number=speech.start()
        events=self.wait_for(speech,'partial')
        speech.finish(number);speech.session['thread'].join(2)
        events+=speech.poll()
        self.assertEqual(sum(kind=='warning' for _,kind,_ in events),1)
        self.assertEqual([payload['partial'] for _,kind,payload in events if kind=='partial'],['add mill','add milk'])
        self.assertTrue(any(kind=='final' for _,kind,_ in events))
        self.assertFalse(any(kind=='error' for _,kind,_ in events))


if __name__=='__main__':unittest.main()
