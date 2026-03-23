# Student Bot Demo — "The Money Demo"

> What Jon shows at ProductHunt. What gets shared on TikTok.

This is a real conversation between a 10th-grade student and EDUagent's student bot, powered by Mr. Mac's teaching persona. The lesson is "Chain Reaction: Why Did a Single Assassination Start a World War?"

**Setup:** Mr. Mac activated Lesson 3 (the powder keg analogy) for class `MR-MAC-P3` with hint mode ON.

---

## The Conversation

**Student:** hey mr mac, we talked about the powder keg thing today but I still don't really get it. like why do they call it a powder keg?

**Teacher:** Great question — and I love that you're thinking about *why* we use that term, not just memorizing it. So think about it this way: what happens when you light a match near a barrel of gunpowder? 💥 It doesn't just burn a little — it *explodes*. Now here's the key: the gunpowder was already dangerous *before* anyone struck the match. The Balkans in 1914 were like that barrel. Nationalism, militarism, imperial competition, secret alliances — all of that tension was packed in and building pressure for *years*. The assassination of Archduke Franz Ferdinand? That was just the match. The explosion was going to happen one way or another. Does that make more sense?

**Student:** ohhhh ok so the assassination didn't cause the war by itself? it was already about to happen?

**Teacher:** Now you're cooking! Exactly. Think of it like this — we talked about MANIA in class today (Militarism, Alliances, Nationalism, Imperialism, Assassination). The first four letters? That's the gunpowder. Years of arms races, secret treaties, intense national pride, and countries grabbing colonies. The A at the end — the assassination — that's just what set it all off. If it hadn't been Gavrilo Princip pulling that trigger in Sarajevo, something *else* probably would have lit the fuse. That's what makes it such a powerful analogy. The *causes* were already in place.

**Student:** ok that makes sense. so for the homework, question 3 asks "what was the most significant cause of WWI?" — is it the alliances?

**Teacher:** Ahh, nice try! 😄 I'm not going to just hand you that one — but I *will* help you think through it. Here's a question for you: the alliances meant that when Austria-Hungary declared war on Serbia, other countries got pulled in. But *why* did those alliances exist in the first place? What were countries afraid of that made them sign those treaties? Think about the other letters in MANIA — which ones *created the need* for alliances?

**Student:** hmm... militarism? like everyone was building up their armies so countries needed allies for protection?

**Teacher:** 🔥 See, you're doing the thinking yourself — that's the whole point! You just made a really strong argument that militarism *drove* the alliance system. Now here's what I want you to do for your answer: pick the cause YOU think is most significant, and then explain *how it connects to the others*. That's what makes a strong historical argument — not just naming one cause, but showing how the pieces fit together. You clearly understand this. Trust your thinking.

**Student:** wait so there's no single right answer??

**Teacher:** Welcome to history! 🎉 There rarely is one "right" answer — what matters is how well you *support* your argument with evidence. A student who argues militarism was the most significant cause and backs it up with specific examples? That's an A answer. A student who argues nationalism? Also an A answer — *if they support it*. That's what we do as historians. We make claims, and then we prove them. You've got this.

**Student:** i get it now! im gonna say militarism because it connects to everything else. thanks mr mac!

**Teacher:** That's what I like to hear! And notice what just happened — you worked through that *yourself*. I didn't give you the answer. You built the argument. That's real learning. Now go write it up — and remember, cite specific evidence from the lesson. I want to see you mention at least one example of the arms race. See you tomorrow. 📚

---

## What This Demonstrates

1. **Teacher voice is authentic** — Mr. Mac's Socratic, encouraging style comes through naturally
2. **Hint mode works** — when the student asked for the homework answer (#3), the bot redirected with guiding questions instead of giving the answer
3. **Lesson context is live** — the bot references MANIA, the powder keg analogy, and specific lesson content
4. **Conversation memory** — each response builds on what was said before
5. **Confusion detection** — "I don't really get it" triggers a targeted explanation using the lesson's direct instruction content
6. **Students learn** — the bot scaffolds understanding until the student arrives at the answer themselves

## Try It Yourself

```bash
# Teacher sets up the class
eduagent chat
> set lesson 3 as active for class MR-MAC-P3

# Student joins
eduagent student-chat --class-code MR-MAC-P3 --student-id student-jaylen --name "Jaylen"
```
