// Shared v2 resume helpers for ATS templates
#let load-resume(path) = {
  let root = yaml(path)
  if "resume" in root { root.resume } else { root }
}

#let contact-parts(p) = {
  let parts = ()
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "github" in p and p.github != none and p.github != "" { parts.push(p.github) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push(p.linkedin) }
  if "portfolio" in p and p.portfolio != none and p.portfolio != "" { parts.push(p.portfolio) }
  parts
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" { [#s – #e] }
  else if s != none and s != "YYYY" { [#s] }
  else if e != none { [#e] }
  else { [] }
}

#let skill-groups(sk) = (
  ("Frontend", if "frontend" in sk { sk.frontend } else { () }),
  ("Backend", if "backend" in sk { sk.backend } else { () }),
  ("Database", if "database" in sk { sk.database } else { () }),
  ("Cloud & Tools", if "cloud_tools" in sk { sk.cloud_tools } else { () }),
  ("Other", if "other" in sk { sk.other } else { () }),
)

#let has-skills(sk) = {
  let groups = skill-groups(sk)
  let found = false
  for (label, items) in groups { if items.len() > 0 { found = true } }
  found
}

#let render-experience(r, body-size) = {
  if "experience" in r and r.experience.len() > 0 {
    for job in r.experience {
      grid(
        columns: (1fr, auto),
        gutter: 8pt,
        text(size: body-size, weight: "bold")[#job.title],
        align(right, text(size: body-size)[#exp-dates(job)]),
      )
      let cl = job.company
      if "location" in job and job.location != none and job.location != "" {
        cl = cl + " — " + job.location
      }
      text(size: body-size)[#cl]
      v(0.12em)
      if "bullets" in job {
        for b in job.bullets { par(hanging-indent: 12pt)[• #b] }
      }
      v(0.4em)
    }
  }
}

#let render-projects(r, body-size) = {
  if "projects" in r and r.projects.len() > 0 {
    for proj in r.projects {
      text(weight: "bold", size: body-size)[#proj.name]
      if "technologies" in proj and proj.technologies.len() > 0 {
        v(0.08em)
        text(size: body-size)[#proj.technologies.join(", ")]
      }
      v(0.1em)
      if "bullets" in proj {
        for b in proj.bullets { par(hanging-indent: 12pt)[• #b] }
      }
      v(0.35em)
    }
  }
}

#let render-skills-inline(r, body-size) = {
  if "skills" in r and has-skills(r.skills) {
    for (label, items) in skill-groups(r.skills) {
      if items.len() > 0 {
        grid(
          columns: (95pt, 1fr),
          gutter: 10pt,
          text(weight: "bold", size: body-size)[#label + ":"],
          [#items.join(", ")],
        )
        v(0.12em)
      }
    }
  }
}

#let render-education(r, body-size) = {
  if "education" in r and r.education.len() > 0 {
    for edu in r.education {
      text(weight: "bold", size: body-size)[#edu.degree]
      v(0.06em)
      text(size: body-size)[#edu.institution#if "graduation" in edu and edu.graduation != none { " · " + edu.graduation }]
      v(0.28em)
    }
  }
}

#let render-certs(r) = {
  if "certifications" in r and r.certifications.len() > 0 {
    for c in r.certifications { par(hanging-indent: 12pt)[• #c] }
  }
}

#let render-custom(r) = {
  if "custom_sections" in r {
    for sec in r.custom_sections {
      for item in sec.items { par(hanging-indent: 12pt)[• #item] }
    }
  }
}
