// ATS Bold — strong hierarchy, thick rules, eye-catching header
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let accent = rgb("#111827")

#set page(paper: "a4", margin: 0.48in)
#set text(font: "Segoe UI", size: body-size, fill: black)
#set par(leading: 0.74em, justify: false)

#let section-title(title) = {
  v(1em)
  text(size: 13pt, weight: "bold", fill: accent)[#upper(title)]
  v(0.12em)
  line(length: 100%, stroke: 2.5pt + accent)
  v(0.35em)
}

#block(width: 100%, inset: (bottom: 10pt))[
  #text(size: 30pt, weight: "bold", fill: accent)[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.12em)
    text(size: 12pt, weight: "semibold")[#r.personal.title]
  }
  #v(0.35em)
  #text(size: 10pt)[#contact-parts(r.personal).join("  |  ")]
]
#line(length: 100%, stroke: 3pt + accent)
#v(0.4em)

#render-ordered-sections(r, section-title, body-size)
