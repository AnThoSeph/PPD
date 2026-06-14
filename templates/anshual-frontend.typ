// Anshual Thomas SDEI Frontend — matches Resume.io export layout
#let resume-path = sys.inputs.at("resume")
#let data = yaml(resume-path)

#let design-path = sys.inputs.at("design", default: none)
#let design = if design-path != none { json(design-path) } else { (:) }

#let header-bg = if "header_bg" in design { rgb(design.header_bg) } else { rgb("#000000") }
#let header-text = if "header_text" in design { rgb(design.header_text) } else { white }
#let main-text = if "main_text" in design { rgb(design.main_text) } else { rgb("#000000") }
#let muted = if "muted" in design { rgb(design.muted) } else { rgb("#333333") }
#let body-font = if "font_body" in design { design.font_body } else { "Century Gothic" }
#let name-size = if "name_size_pt" in design { design.name_size_pt * 1pt } else { 29pt }
#let section-size = if "section_size_pt" in design { design.section_size_pt * 1pt } else { 14pt }
#let body-size = if "body_size_pt" in design { design.body_size_pt * 1pt } else { 11pt }
#let margin-x = if "page_margin_x_pt" in design { design.page_margin_x_pt * 1pt } else { 37pt }
#let margin-y = if "page_margin_y_pt" in design { design.page_margin_y_pt * 1pt } else { 20pt }

#set page(paper: "a4", margin: (x: margin-x, y: margin-y))
#set text(font: body-font, size: body-size, fill: main-text)
#set par(leading: 0.72em, justify: false)

#let contact-line() = {
  let parts = ()
  if "location" in data.basics and data.basics.location != none { parts.push(data.basics.location) }
  if "phone" in data.basics and data.basics.phone != none { parts.push(data.basics.phone) }
  if "email" in data.basics and data.basics.email != none { parts.push(data.basics.email) }
  if "links" in data.basics {
    for link in data.basics.links {
      parts.push(link.label + ": " + link.url)
    }
  }
  parts.join(" | ")
}

#let section-title(content) = {
  v(1.1em)
  text(size: section-size, weight: "bold", fill: main-text)[#content]
  v(0.25em)
  line(length: 100%, stroke: 0.6pt + main-text)
  v(0.45em)
}

#let date-range(item) = {
  let start = if "start" in item { item.start } else { none }
  let end = if "end" in item { item.end } else { none }
  if start != none and end != none and start != "YYYY" {
    [#start to #end]
  } else if start != none and start != "YYYY" {
    [#start]
  } else if end != none {
    [#end]
  } else {
    []
  }
}

// Name
#text(size: name-size, weight: "bold", fill: main-text)[#data.basics.name]
#if "title" in data.basics and data.basics.title != none {
  v(0.15em)
  text(size: body-size, fill: muted)[#data.basics.title]
}
#v(0.55em)

// Contact header bar
#block(
  width: 100%,
  fill: header-bg,
  inset: (x: 10pt, y: 10pt),
)[
  #text(size: 10pt, fill: header-text)[#contact-line()]
]

#if "summary" in data and data.summary != none and data.summary != "" {
  section-title("Professional Summary")
  par(leading: 0.75em)[#data.summary]
}

#if "experience" in data and data.experience.len() > 0 {
  section-title("Work History")
  for job in data.experience {
    v(0.15em)
    grid(
      columns: (1fr, auto),
      text(size: body-size, weight: "bold")[#job.role],
      align(right, text(size: body-size)[#date-range(job)]),
    )
    text(size: body-size)[
      #job.company
      #if "location" in job and job.location != none { [ — #job.location] }
    ]
    v(0.1em)
    if "bullets" in job {
      for bullet in job.bullets {
        grid(
          columns: (14pt, 1fr),
          align(top, text(size: 12pt)[•]),
          par(leading: 0.72em)[#text(size: body-size)[#bullet]],
        )
        v(0.08em)
      }
    }
    v(0.35em)
  }
}

#if "projects" in data and data.projects.len() > 0 {
  section-title("Projects")
  for proj in data.projects {
    v(0.15em)
    text(size: body-size, weight: "bold")[#proj.name]
    if "description" in proj and proj.description != none {
      v(0.05em)
      text(size: body-size, fill: muted)[#proj.description]
    }
    if "bullets" in proj {
      for bullet in proj.bullets {
        grid(
          columns: (14pt, 1fr),
          align(top, text(size: 12pt)[•]),
          par(leading: 0.72em)[#text(size: body-size)[#bullet]],
        )
        v(0.08em)
      }
    }
    v(0.25em)
  }
}

#if "skills" in data and data.skills.len() > 0 {
  section-title("Skills")
  for group in data.skills {
    v(0.2em)
    grid(
      columns: (110pt, 1fr),
      gutter: 16pt,
      text(size: body-size, weight: "bold")[#group.category],
      par(leading: 0.72em)[#group.items.join(", ")],
    )
  }
}

#if "education" in data and data.education.len() > 0 {
  section-title("Education")
  for edu in data.education {
    v(0.15em)
    grid(
      columns: (1fr, auto),
      text(size: body-size, weight: "bold")[#edu.degree],
      align(right)[
        #if "end" in edu and edu.end != none {
          text(size: body-size)[#edu.end]
        }
      ],
    )
    text(size: body-size)[#edu.institution]
    if "details" in edu {
      for detail in edu.details {
        v(0.05em)
        text(size: body-size)[#detail]
      }
    }
    v(0.25em)
  }
}

#if "certifications" in data and data.certifications.len() > 0 {
  section-title("Certifications")
  for cert in data.certifications {
    grid(
      columns: (14pt, 1fr),
      align(top, text(size: 12pt)[•]),
      text(size: body-size)[#cert.name],
    )
    v(0.08em)
  }
}
