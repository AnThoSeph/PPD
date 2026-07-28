// ATS Elegant — refined serif, centered header, classic feel
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt

#set page(paper: "a4", margin: 0.55in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.78em, justify: false)

#let section-title(title) = {
  v(1em)
  align(center)[#text(size: 12pt, weight: "bold", style: "italic")[#title]]
  v(0.1em)
  align(center)[#line(length: 35%, stroke: 0.75pt + black)]
  v(0.35em)
}

#align(center)[
  #text(size: 28pt, weight: "bold")[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.15em)
    text(size: 12pt, style: "italic")[#r.personal.title]
  }
  #v(0.35em)
  #text(size: 10pt)[#contact-parts(r.personal).join(" · ")]
]

#render-ordered-sections(r, section-title, body-size)
