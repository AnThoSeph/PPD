// ATS Swiss — grid-precise, Helvetica-style, uppercase micro-labels
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10pt

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Arial", size: body-size, fill: black)
#set par(leading: 0.7em, justify: false)

#let section-title(title) = {
  v(0.9em)
  text(size: 9pt, weight: "bold", tracking: 0.18em)[#upper(title)]
  v(0.25em)
}

#text(size: 24pt, weight: "bold", tracking: -0.02em)[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.08em)
  text(size: 10.5pt)[#upper(r.personal.title)]
}
#v(0.3em)
#grid(
  columns: (1fr, 1fr),
  gutter: 8pt,
  text(size: 9pt)[#contact-parts(r.personal).join(" / ")],
  [],
)
#v(0.2em)
#line(length: 100%, stroke: 1.25pt + black)

#render-ordered-sections(r, section-title, body-size, summary-title: "Profile")
