// ATS Professional — traditional left-aligned, v2 YAML
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }
#import "ats-v2-lib.typ": render-ordered-sections
#let body-size = 11pt

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.75em, justify: false)

#let contact-parts = {
  let parts = ()
  let p = r.personal
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push(p.linkedin) }
  parts
}

#let section-title(title) = {
  v(1em)
  text(size: 12pt, weight: "bold")[#title]
  v(0.1em)
  line(length: 100%, stroke: 0.75pt + black)
  v(0.35em)
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" { [#s – #e] }
  else if s != none and s != "YYYY" { [#s] }
  else if e != none { [#e] }
  else { [] }
}

#text(size: 26pt, weight: "bold")[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.1em)
  text(size: 12pt)[#r.personal.title]
}
#v(0.25em)
#text(size: 10pt)[#contact-parts.join("   |   ")]
#v(0.35em)
#line(length: 100%, stroke: 1pt + black)

#render-ordered-sections(r, section-title, body-size,
  summary-title: "Professional Summary",
  experience-title: "Professional Experience",
)
