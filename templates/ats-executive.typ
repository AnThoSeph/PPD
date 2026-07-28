// ATS Executive — navy accents, authoritative layout
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let navy = rgb("#1e3a5f")

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.76em, justify: false)

#let section-title(title) = {
  v(0.95em)
  text(size: 11.5pt, weight: "bold", fill: navy)[#title]
  v(0.08em)
  line(length: 100%, stroke: 0.5pt + navy)
  v(0.32em)
}

#text(size: 27pt, weight: "bold", fill: navy)[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.12em)
  text(size: 12pt)[#r.personal.title]
}
#v(0.3em)
#text(size: 10pt)[#contact-parts(r.personal).join("  |  ")]
#v(0.25em)
#line(length: 100%, stroke: 0.5pt + navy)
#v(0.05em)
#line(length: 100%, stroke: 2pt + navy)

#render-ordered-sections(r, section-title, body-size,
  summary-title: "Executive Summary",
  experience-title: "Professional Experience",
  projects-title: "Key Projects",
  skills-title: "Core Competencies",
)
