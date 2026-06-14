// Resume.io-style sidebar — multi-page (sidebar stripe repeats on every page)
#let resume-path = sys.inputs.at("resume")
#let data = yaml(resume-path)

#let design-path = sys.inputs.at("design", default: none)
#let design = if design-path != none { json(design-path) } else { (:) }

#let sidebar-bg = if "sidebar_bg" in design { rgb(design.sidebar_bg) } else { rgb("#2d3e50") }
#let accent = if "accent" in design { rgb(design.accent) } else { rgb("#0891b2") }
#let main-text = if "main_text" in design { rgb(design.main_text) } else { rgb("#1a1a1a") }
#let muted = if "muted" in design { rgb(design.muted) } else { rgb("#555555") }
#let sidebar-text = white
#let sidebar-width = 31%

#set page(
  paper: "a4",
  margin: (left: sidebar-width + 22pt, top: 20pt, right: 22pt, bottom: 20pt),
  background: place(
    left + top,
    rect(width: sidebar-width, height: 100%, fill: sidebar-bg),
  ),
)

#set text(font: "Segoe UI", size: 10pt, fill: main-text)
#show link: set text(fill: accent)

#let section-title(content) = {
  v(0.35em)
  text(size: 11pt, weight: "bold", fill: accent, tracking: 0.08em)[#upper(content)]
  v(0.12em)
  line(length: 100%, stroke: 0.6pt + accent)
  v(0.3em)
}

#let sidebar-title(content) = {
  v(0.45em)
  text(size: 9.5pt, weight: "bold", fill: sidebar-text, tracking: 0.1em)[#upper(content)]
  v(0.2em)
}

#let contact-row(label, value) = {
  if value != none and value != "" {
    v(0.15em)
    text(size: 8.8pt, fill: sidebar-text.lighten(10%))[#strong(label) #value]
  }
}

#let date-range(item) = {
  let start = if "start" in item { item.start } else { none }
  let end = if "end" in item { item.end } else { none }
  if start != none and end != none and start != "YYYY" {
    [#start – #end]
  } else if start != none and start != "YYYY" {
    [#start]
  } else if end != none {
    [#end]
  } else {
    []
  }
}

// Sidebar content — first page only; stripe continues on later pages
#place(
  left + top,
  dx: 14pt,
  dy: 20pt,
  block(width: sidebar-width - 28pt)[
    #if "title" in data.basics and data.basics.title != none {
      text(size: 10pt, weight: "bold", fill: sidebar-text)[#data.basics.title]
      v(0.4em)
    }
    #sidebar-title("Contact")
    #if "email" in data.basics { contact-row("Email:", data.basics.email) }
    #if "phone" in data.basics { contact-row("Phone:", data.basics.phone) }
    #if "location" in data.basics { contact-row("Location:", data.basics.location) }
    #if "links" in data.basics {
      for link in data.basics.links {
        contact-row(link.label + ":", link.url)
      }
    }

    #if "skills" in data and data.skills.len() > 0 {
      sidebar-title("Skills")
      for group in data.skills {
        v(0.12em)
        text(size: 8.8pt, weight: "bold", fill: sidebar-text)[#group.category]
        v(0.08em)
        for skill in group.items {
          text(size: 8.5pt, fill: sidebar-text.lighten(15%))[• #skill]
          v(0.04em)
        }
      }
    }

    #if "certifications" in data and data.certifications.len() > 0 {
      sidebar-title("Certifications")
      for cert in data.certifications {
        v(0.12em)
        text(size: 8.5pt, fill: sidebar-text)[#cert.name]
        if "issuer" in cert and cert.issuer != none {
          text(size: 8pt, fill: sidebar-text.lighten(20%))[ — #cert.issuer]
        }
      }
    }
  ],
)

// Main column — flows naturally across pages
#text(size: 24pt, weight: "bold", fill: main-text)[#data.basics.name]
#v(0.5em)

#if "summary" in data and data.summary != none and data.summary != "" {
  section-title("Professional Summary")
  par(justify: true, leading: 0.65em)[#data.summary]
}

#if "experience" in data and data.experience.len() > 0 {
  section-title("Work History")
  for job in data.experience {
    v(0.2em)
    grid(
      columns: (1fr, auto),
      text(size: 10.5pt, weight: "bold")[#job.role],
      align(right, text(size: 9pt, fill: muted)[#date-range(job)]),
    )
    text(size: 10pt, weight: "semibold", fill: accent)[#job.company]
    if "location" in job and job.location != none {
      text(size: 9pt, fill: muted)[ — #job.location]
    }
    v(0.12em)
    if "bullets" in job {
      for bullet in job.bullets {
        grid(
          columns: (8pt, 1fr),
          text(size: 9pt)[•],
          par(leading: 0.62em)[#text(size: 9.5pt, fill: main-text)[#bullet]],
        )
        v(0.06em)
      }
    }
    v(0.3em)
  }
}

#if "projects" in data and data.projects.len() > 0 {
  section-title("Projects")
  for proj in data.projects {
    v(0.15em)
    text(size: 10.5pt, weight: "bold")[#proj.name]
    if "description" in proj and proj.description != none {
      text(size: 9.5pt, fill: muted)[ — #proj.description]
    }
    if "bullets" in proj {
      for bullet in proj.bullets {
        v(0.06em)
        grid(
          columns: (8pt, 1fr),
          text(size: 9pt)[•],
          text(size: 9.5pt)[#bullet],
        )
      }
    }
    v(0.2em)
  }
}

#if "education" in data and data.education.len() > 0 {
  section-title("Education")
  for edu in data.education {
    v(0.15em)
    text(size: 10.5pt, weight: "bold")[#edu.degree]
    v(0.05em)
    text(size: 10pt, fill: accent)[#edu.institution]
    if "end" in edu and edu.end != none {
      text(size: 9pt, fill: muted)[ (#edu.end)]
    }
    if "details" in edu {
      for detail in edu.details {
        v(0.06em)
        text(size: 9.5pt)[#detail]
      }
    }
    v(0.15em)
  }
}
