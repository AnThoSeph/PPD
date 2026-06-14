// ATS Professional — traditional left-aligned, v2 YAML
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: 11pt, fill: black)
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

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Professional Summary")
  par(leading: 0.78em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Professional Experience")
  for job in r.experience {
    grid(columns: (1fr, auto), gutter: 8pt, text(weight: "bold")[#job.title], align(right, exp-dates(job)))
    text(style: "italic")[#job.company#if "location" in job and job.location != none { ", " + job.location }]
    v(0.15em)
    for b in job.bullets { par(hanging-indent: 14pt)[• #b] }
    v(0.45em)
  }
}

#if "projects" in r and r.projects.len() > 0 {
  section-title("Projects")
  for proj in r.projects {
    text(weight: "bold")[#proj.name]
    if "technologies" in proj and proj.technologies.len() > 0 {
      v(0.08em)
      text(size: 10pt)[#proj.technologies.join(", ")]
    }
    v(0.1em)
    for b in proj.bullets { par(hanging-indent: 14pt)[• #b] }
    v(0.35em)
  }
}

#if "skills" in r {
  let sk = r.skills
  let groups = (
    ("Technical Skills", if "frontend" in sk { sk.frontend + sk.backend + sk.database + sk.cloud_tools + sk.other } else { () }),
  )
  let flat = ()
  if "frontend" in sk { flat += sk.frontend }
  if "backend" in sk { flat += sk.backend }
  if "database" in sk { flat += sk.database }
  if "cloud_tools" in sk { flat += sk.cloud_tools }
  if "other" in sk { flat += sk.other }
  if flat.len() > 0 {
    section-title("Skills")
    flat.join("  ·  ")
  }
}

#if "education" in r and r.education.len() > 0 {
  section-title("Education")
  for edu in r.education {
    grid(columns: (1fr, auto), text(weight: "bold")[#edu.degree], align(right)[#if "graduation" in edu and edu.graduation != none { edu.graduation }])
    text(size: 10pt)[#edu.institution]
    v(0.3em)
  }
}

#if "certifications" in r and r.certifications.len() > 0 {
  section-title("Certifications")
  for c in r.certifications { par(hanging-indent: 14pt)[• #c] }
}

#if "custom_sections" in r {
  for sec in r.custom_sections {
    section-title(sec.title)
    for item in sec.items { par(hanging-indent: 14pt)[• #item] }
  }
}
