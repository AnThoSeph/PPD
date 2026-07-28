// ATS-standard resume — single column, black on white, v2 YAML schema
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }
#import "ats-v2-lib.typ": render-ordered-sections
#let body-size = 10.5pt

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.72em, justify: false)

#let contact-parts = {
  let parts = ()
  let p = r.personal
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "github" in p and p.github != none and p.github != "" { parts.push("GitHub: " + p.github) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push("LinkedIn: " + p.linkedin) }
  if "portfolio" in p and p.portfolio != none and p.portfolio != "" { parts.push("Portfolio: " + p.portfolio) }
  parts
}

#let section-title(title) = {
  v(0.85em)
  text(size: 12pt, weight: "bold")[#title]
  v(0.35em)
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" {
    [#s – #e]
  } else if s != none and s != "YYYY" {
    [#s]
  } else if e != none {
    [#e]
  } else {
    []
  }
}

#align(center)[
  #text(size: 22pt, weight: "bold")[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.2em)
    text(size: 11pt)[#r.personal.title]
  }
  #v(0.35em)
  #text(size: 9.5pt)[#contact-parts.join(" | ")]
]

#render-ordered-sections(r, section-title, body-size)
