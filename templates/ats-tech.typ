// ATS Tech — sharp sans-serif, accent rule, developer-friendly
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let accent = rgb("#0d9488")

#set page(paper: "a4", margin: 0.45in)
#set text(font: "Segoe UI", size: body-size, fill: rgb("#111"))
#set par(leading: 0.72em, justify: false)

#let section-title(title) = {
  v(0.85em)
  grid(
    columns: (auto, 1fr),
    gutter: 10pt,
    align(left + horizon, text(size: 10pt, weight: "bold", fill: accent)[#upper(title)]),
    align(left + horizon, line(length: 100%, stroke: 0.8pt + accent)),
  )
  v(0.3em)
}

#grid(
  columns: (1fr, auto),
  gutter: 12pt,
  [
    #text(size: 26pt, weight: "bold")[#r.personal.name]
    #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
      v(0.1em)
      text(size: 11pt, fill: rgb("#374151"))[#r.personal.title]
    }
  ],
  align(right + top)[
    #text(size: 9pt, fill: rgb("#374151"))[
      #for (i, part) in contact-parts(r.personal).enumerate() [
        #if i > 0 [ \ ]
        #part
      ]
    ]
  ],
)
#v(0.15em)
#line(length: 100%, stroke: 2pt + accent)

#render-ordered-sections(r, section-title, body-size, summary-title: "Summary")
