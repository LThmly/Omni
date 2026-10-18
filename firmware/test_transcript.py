"""Streaming text stays stable while new/corrected words blend into place."""
import unittest
from transcript import TranscriptAnimator,short_response


def measure(text):return len(text)*10


class TranscriptTest(unittest.TestCase):
    def setUp(self):self.animator=TranscriptAnimator()

    def test_short_responses_fit_one_line_and_preserve_brief_answers(self):
        self.assertEqual(short_response('Opening settings.',measure),'Opening settings.')
        for source in ('Many words in a long reply that should be kept concise.', 'W'*200,
                       'First line\nSecond line\nThird line\nFourth line'):
            text=short_response(source,measure,width=160)
            self.assertLessEqual(measure(text),160)
            self.assertLessEqual(len(text),48)
            self.assertLessEqual(len(text.split()),6)
            self.assertNotIn('\n',text)

    def update(self,text,now,**kwargs):
        self.animator.update(text,now,measure,**kwargs)

    def test_append_keeps_existing_words_fixed_and_reveals_new_words(self):
        self.update('add milk',0)
        before=list(self.animator.frames(300))
        self.update('add milk to my list',350)
        during=list(self.animator.frames(350))
        self.assertEqual(during[:2],before)
        self.assertEqual([opacity for _,_,_,opacity in during[2:]],[0,0,0])
        midpoint=list(self.animator.frames(450))
        self.assertTrue(all(0<opacity<1 for _,_,_,opacity in midpoint[2:]))
        settled=list(self.animator.frames(650))
        self.assertTrue(all(opacity==1 for _,_,_,opacity in settled))
        self.assertEqual(self.animator.text,'add milk to my list')

    def test_correction_only_replaces_changed_word_and_removes_old_hypothesis(self):
        self.update('add mill',0)
        self.update('add milk',300)
        self.assertEqual(self.animator.text,'add milk')
        early=list(self.animator.frames(300))
        self.assertEqual(next(frame for frame in early if frame[0]=='add'),('add',0,0,1))
        self.assertEqual(next(frame[3] for frame in early if frame[0]=='milk'),0)
        middle=list(self.animator.frames(380))
        self.assertTrue(0<next(frame[3] for frame in middle if frame[0]=='mill')<1)
        self.assertTrue(0<next(frame[3] for frame in middle if frame[0]=='milk')<1)
        self.assertEqual([frame[0] for frame in self.animator.frames(600)],['add','milk'])

    def test_repeated_hypotheses_do_not_restart_reveal(self):
        self.update('hello world',0)
        self.update('hello world',100)
        self.update('hello world',200)
        self.assertTrue(all(frame[3]==1 for frame in self.animator.frames(300)))

    def test_new_partials_do_not_restart_unchanged_word_movement_or_scroll(self):
        self.update('one two three four',0,width=80)
        self.update('one two three four five',300,width=80)
        scroll_started=self.animator.scroll_at
        first=self.animator.words[0]
        movement_started=first.moved_at
        self.update('one two three four five six',350,width=80)
        self.assertEqual(self.animator.scroll_at,scroll_started)
        self.assertEqual(first.moved_at,movement_started)
        self.assertEqual(self.animator.scroll(510),self.animator.scroll_to)

    def test_wrapping_scrolls_smoothly_and_keeps_latest_two_lines(self):
        self.update('one two',0,width=80)
        self.update('one two three four five six',300,width=80)
        target=self.animator.scroll_to
        self.assertGreater(target,0)
        self.assertEqual(self.animator.scroll(300),0)
        self.assertTrue(0<self.animator.scroll(400)<target)
        settled=list(self.animator.frames(650))
        visible=[word for word,x,y,a in settled if 0<=y<54]
        self.assertEqual(visible,['four','five','six'])
        self.assertEqual(len({y for _,_,y,a in settled if 0<=y<54 and a>0}),2)

    def test_speech_viewport_keeps_three_lines_and_scrolls_only_when_needed(self):
        self.update('one two three four',0,width=80,visible_lines=3)
        self.assertEqual(self.animator.scroll_to,0)
        self.update('one two three four five six',300,width=80,visible_lines=3)
        frames=list(self.animator.frames(650))
        self.assertEqual(len({y for _,_,y,a in frames if 0<=y<81 and a>0}),3)
        self.assertEqual([word for word,_,y,a in frames if 0<=y<81],['three','four','five','six'])

    def test_reduced_motion_skips_fade_movement_and_retired_words(self):
        self.update('add mill',0,animate=False)
        self.update('add milk',1,animate=False)
        self.assertEqual(list(self.animator.frames(1)),[('add',0,0,1),('milk',40,0,1)])
        self.assertFalse(self.animator.retired)
        self.update('one two three four',2,width=60,animate=False)
        self.assertEqual(self.animator.scroll(2),self.animator.scroll_to)

    def test_centered_lines_have_balanced_margins_and_ease_when_appended(self):
        self.update('add milk',0,width=200,align='center')
        before=list(self.animator.frames(300))
        self.assertEqual(before[0][1],60)
        self.assertEqual(before[-1][1]+measure(before[-1][0]),140)
        self.update('add milk to my list',350,width=200,align='center')
        during=list(self.animator.frames(350))
        self.assertEqual(during[0][1],before[0][1])
        settled=list(self.animator.frames(650))
        left=min(x for _,x,_,_ in settled)
        right=max(x+measure(word) for word,x,_,_ in settled)
        self.assertEqual(left,200-right)

    def test_long_tokens_fit_and_clearing_resets_the_next_recording(self):
        self.update('A'*50,0,width=80)
        self.assertTrue(all(measure(word)<=80 for word,_,_,_ in self.animator.frames(300)))
        self.animator.clear()
        self.update('new request',400)
        self.assertEqual(self.animator.scroll(400),0)
        self.assertFalse(self.animator.retired)


if __name__=='__main__':unittest.main()
