// ATS Creative — contemporary layout, split header band (text-only, ATS-safe)
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let ink = rgb("#18181b")
#let warm = rgb("#7c2d12")

#set page(paper: "a4", margin: (x: 0.5in, top: 0.42in, bottom: 0.5in))
#set text(font: "Segoe UI", size: body-size, fill: ink)
#set par(leading: 0.74em, justify: false)

#let section-title(title) = {
  v(0.85em)
  grid(
    columns: (3pt, 1fr),
    gutter: 8pt,
    rect(width: 3pt, height: 1.1em, fill: warm),
    text(size: 11.5pt, weight: "bold")[#title],
  )
  v(0.28em)
}

#block(
  width: 100%,
  inset: (x: 0pt, y: 12pt),
  stroke: (bottom: 1.5pt + warm),
)[
  #grid(
    columns: (2fr, 1fr),
    gutter: 16pt,
    [
      #text(size: 28pt, weight: "bold")[#r.personal.name]
      #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
        v(0.1em)
        text(size: 11.5pt, fill: warm)[#r.personal.title]
      }
    ],
    align(right + horizon)[
      #text(size: 9pt)[
        #for (i, part) in contact-parts(r.personal).enumerate() [
          #if i > 0 [ \ ]
          #part
        ]
      ]
    ],
  )
]

#render-ordered-sections(r, section-title, body-size)
