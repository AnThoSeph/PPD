// ATS Modern — sans-serif, centered, v2 YAML
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }
#import "ats-v2-lib.typ": render-ordered-sections
#let body-size = 10.5pt

#set page(paper: "a4", margin: 0.45in)
#set text(font: "Segoe UI", size: body-size, fill: black)
#set par(leading: 0.74em, justify: false)

#let contact-parts = {
  let parts = ()
  let p = r.personal
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "github" in p and p.github != none and p.github != "" { parts.push(p.github) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push(p.linkedin) }
  parts
}

#let section-title(title) = {
  v(0.9em)
  align(center)[#text(size: 11pt, weight: "bold", tracking: 0.06em)[#upper(title)]]
  v(0.15em)
  line(length: 100%, stroke: 0.5pt + black)
  v(0.3em)
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" { [#s – #e] }
  else if s != none and s != "YYYY" { [#s] }
  else if e != none { [#e] }
  else { [] }
}

#align(center)[
  #text(size: 24pt, weight: "bold")[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.15em)
    text(size: 11pt, fill: rgb("#333"))[#r.personal.title]
  }
  #v(0.3em)
  #text(size: 9.5pt, fill: rgb("#444"))[#contact-parts.join("  ·  ")]
]

#render-ordered-sections(r, section-title, body-size)
