// ATS Minimal — airy whitespace, subtle gray typography
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let muted = rgb("#4b5563")

#set page(paper: "a4", margin: 0.65in)
#set text(font: "Segoe UI", size: body-size, fill: rgb("#1f2937"))
#set par(leading: 0.82em, justify: false)

#let section-title(title) = {
  v(1.4em)
  text(size: 9pt, weight: "bold", fill: muted, tracking: 0.14em)[#upper(title)]
  v(0.45em)
}

#text(size: 26pt, weight: "light", tracking: 0.02em)[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.2em)
  text(size: 11pt, fill: muted)[#r.personal.title]
}
#v(0.5em)
#text(size: 9.5pt, fill: muted)[#contact-parts(r.personal).join("   ·   ")]

#render-ordered-sections(r, section-title, body-size, summary-title: "Summary")
