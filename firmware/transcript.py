"""Presentation-only smoothing for evolving ASR hypotheses."""
from dataclasses import dataclass


def ease(progress):
    progress=max(0.0,min(1.0,progress))
    return 1-(1-progress)**3


@dataclass
class Word:
    text: str
    x: float
    y: float
    old_x: float
    old_y: float
    moved_at: float
    born_at: float
    retired_at: float | None = None
    retired_alpha: float = 1.0


class TranscriptAnimator:
    FADE_MS=160
    MOVE_MS=180
    SCROLL_MS=210

    def __init__(self):
        self.clear()

    def clear(self):
        self.text=''
        self.words=[]
        self.retired=[]
        self.animate=True
        self.style=None
        self.scroll_from=self.scroll_to=0.0
        self.scroll_at=0.0

    def scroll(self,now):
        if not self.animate:return self.scroll_to
        t=ease((now-self.scroll_at)/self.SCROLL_MS)
        return self.scroll_from+(self.scroll_to-self.scroll_from)*t

    def position(self,word,now):
        if not self.animate:return word.x,word.y
        t=ease((now-word.moved_at)/self.MOVE_MS)
        return word.old_x+(word.x-word.old_x)*t,word.old_y+(word.y-word.old_y)*t

    def opacity(self,word,now):
        if not self.animate:return 1.0
        if word.retired_at is not None:
            return word.retired_alpha*(1-ease((now-word.retired_at)/self.FADE_MS))
        t=max(0.0,min(1.0,(now-word.born_at)/self.FADE_MS))
        return t*t*(3-2*t)

    def update(self,text,now,measure,width=408,line_height=27,animate=True,align='left'):
        text=' '.join(text.split())
        style=(width,line_height,align)
        if text==self.text and style==self.style and animate==self.animate:return
        old_scroll=self.scroll(now)
        # Word wrapping keeps existing prefixes fixed. Split oversized tokens so
        # even a pasted URL fits without clipping every subsequent update.
        tokens=[]
        for word in text.split():
            chunk=''
            for character in word:
                if chunk and measure(chunk+character)>width:
                    tokens.append((chunk,False));chunk=''
                chunk+=character
            if chunk:tokens.append((chunk,True))
        targets=[];x=y=0
        for i,(word,space_after) in enumerate(tokens):
            size=measure(word)
            if x and x+size>width:x=0;y+=line_height
            targets.append((word,x,y))
            x+=size+(measure(' ') if space_after else 0)
        if align=='center':
            line_ends={}
            for word,tx,ty in targets:
                line_ends[ty]=max(line_ends.get(ty,0),tx+measure(word))
            targets=[(word,tx+(width-line_ends[ty])/2,ty) for word,tx,ty in targets]
        old=self.words
        prefix=0
        while prefix<min(len(old),len(targets)) and old[prefix].text==targets[prefix][0]:prefix+=1
        suffix=0
        while suffix<min(len(old)-prefix,len(targets)-prefix) and old[-1-suffix].text==targets[-1-suffix][0]:suffix+=1
        keep={i:old[i] for i in range(prefix)}
        for offset in range(suffix):keep[len(targets)-1-offset]=old[-1-offset]
        kept_ids={id(word) for word in keep.values()}
        self.retired=[word for word in self.retired if self.opacity(word,now)>.01]
        if animate:
            for word in old:
                if id(word) in kept_ids:continue
                alpha=self.opacity(word,now)
                px,py=self.position(word,now)
                self.retired.append(Word(word.text,px,py,px,py,now,word.born_at,now,alpha))
        else:self.retired=[]
        words=[];fresh=0
        for i,(text_word,tx,ty) in enumerate(targets):
            if i in keep:
                word=keep[i]
                px,py=self.position(word,now)
                word.old_x,word.old_y=px,py
                word.x,word.y=tx,ty
                word.moved_at=now
            else:
                word=Word(text_word,tx,ty,tx,ty,now,now+min(fresh*18,72))
                fresh+=1
            words.append(word)
        self.words=words;self.text=text;self.style=style;self.animate=animate
        self.scroll_from=old_scroll
        self.scroll_to=max(0,y-line_height)
        self.scroll_at=now

    def settled(self,now):
        """True once the currently presented text has finished fading/moving."""
        if not self.animate:return True
        ends=[self.scroll_at+self.SCROLL_MS]
        ends.extend(max(word.born_at+self.FADE_MS,word.moved_at+self.MOVE_MS) for word in self.words)
        ends.extend(word.retired_at+self.FADE_MS for word in self.retired)
        return now>=max(ends)

    def frames(self,now):
        """Word, x, y, opacity tuples in the two-line viewport."""
        self.retired=[word for word in self.retired if self.opacity(word,now)>.01]
        scroll=self.scroll(now)
        for word in self.retired+self.words:
            x,y=self.position(word,now)
            alpha=self.opacity(word,now)
            # New words lift by just three pixels as they fade into the baseline.
            if word.retired_at is None and self.animate:y+=3*(1-alpha)
            yield word.text,x,y-scroll,alpha
