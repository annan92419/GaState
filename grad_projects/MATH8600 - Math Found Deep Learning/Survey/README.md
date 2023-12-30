# Deciphering Emotions: A Survey of Conversation-based Recognition Methods

---

### Abstract

Emotion Recognition in Conversation (ERC) is an increasingly popular, yet unresolved,
and challenging task in Natural Language Processing. Its aim is to identify the emotional
states of speakers engaged in dialogue. ERC has various applications in human-computer
interaction, social media analysis, mental health assessment, and affective computing.
Solving the ERC task is a necessary step towards creating an empathetic Autonomous
Digital Human (ADH). An ADH is an entity finely attuned to emotions, enhancing its
ability to engage users in a profoundly natural and empathetic manner. In this survey, we
review recent advances in ERC methods, particularly focusing on multimodal approaches
that utilize various information sources like text, audio, and visual cues. We categorize
existing methods into two types: RNN-based and transformer-based, then discuss their
respective advantages and disadvantages. Additionally, we compare their performance
using two widely-used benchmark datasets: IEMOCAP (dyadic) and MELD (dialogue).
Furthermore, we present the primary challenges and open issues in ERC, highlighting
potential directions for future research.

---

### Current ERC Models

| Model             | Year | IEMOCAP | MELD |
|-------------------|:----:|------------:|----------:|
| CNN [x]           | 2014 |      48.18  |     55.02 |
| CMN [x]           | 2018 |      56.13  |      --  |
| DialogueRNN [x]   | 2018 |      62.75  |     57.03 |
| Hi-Trans [x]      | 2020 |      64.50  |     61.94 |
| DialogXL [x]      | 2020 |      65.94  |     62.41 | 
| EmoBERTa [x]      | 2020 |      **67.42**  |     65.61 | 
| M2FNet [x]        | 2022 |      66.20  |     **66.23** | 
| MultiEMO [x]      | 2023 |      64.48  |     61.23 | 
| BC-LSTM [\+]       | 2017 |      56.19  |     56.32 | 
| DialogueTRM [\+]   | 2020 |      69.23  |     63.55 | 
| M2FNet [\+]        | 2022 |      69.89  |     66.71 | 
| FacialMMT [\+]     | 2023 |       --     |     66.58 | 
| MultiEMO [\+]      | 2023 |      **72.84**  |     **66.74** | 

**Table 3.1: Quantitative (F1 weighted average score) comparison with <br>
text-only and multi-modal based on IEMOCAP and MELD benchmarks.**

**Key:** [x] Text-only     [\+] Multi-modal

---

### Remarks

The trends revolve around two major architectures: RNN variants (such as GRU), providing the model with a memory
of preceding utterances, and transformer-based models, enabling the modeling of inter- and
intra-speaker dependencies in utterances. Models like MultiEMO and DialogueTRM
that introduced novel fusion mechanisms showed performance improvements. Therefore,
future research might benefit from exploring novel methods to maintain contextualized information
in uni-modal features and examining the apparent correlation of context within
different modalities. The results presented in Table 3.1 highlight the importance of an
attention mechanism in a model’s architecture to learn crucial segments of an utterance for
the ERC task.
