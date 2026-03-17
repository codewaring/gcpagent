from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


OUT_DIR = Path("/Users/jackyt/Documents/github02/jd-agent-gcp/tmp_resumes_pdf_v1")
OUT_DIR.mkdir(parents=True, exist_ok=True)


CANDIDATES = [
    {
        "file": "resume_001_maria_santos_dba_high.pdf",
        "name": "Maria Santos",
        "role": "Database Administrator",
        "candidate_id": "CAND-001",
        "location": "Manila, Philippines",
        "experience_years": "8 years",
        "phone": "+63 917 555 1001",
        "email": "maria.santos@example.com",
        "summary": "Database Administrator with 8 years of telecom and fintech experience managing Oracle, PostgreSQL, and SQL Server platforms. Strong in HA architecture, performance tuning, backup and recovery, and security hardening.",
        "skills": [
            "Oracle 12c/19c, PostgreSQL, MS SQL Server",
            "SQL tuning, index strategy, query optimization",
            "RMAN, PITR, disaster recovery planning",
            "Linux administration, shell scripting, Python automation",
            "Cloud databases: Google Cloud SQL, AWS RDS",
            "Monitoring: Grafana, Prometheus, Oracle Enterprise Manager",
        ],
        "experience": [
            "Senior Database Administrator, Manila Digital Networks (2022-2026): Managed 40+ production databases and improved P1 incident rate by 35% through proactive patching and monitoring.",
            "Database Administrator, Metro Fintech Systems (2018-2022): Improved critical query performance by 45% and implemented monthly restore validation to ensure DR readiness.",
        ],
        "education": "BS Computer Science, University of the Philippines",
        "certifications": ["Oracle Certified Professional (OCP)", "Google Professional Cloud Database Engineer"],
    },
    {
        "file": "resume_002_kevin_ramos_dba_medium.pdf",
        "name": "Kevin Ramos",
        "role": "Database Administrator",
        "candidate_id": "CAND-002",
        "location": "Quezon City, Philippines",
        "experience_years": "4 years",
        "phone": "+63 917 555 1002",
        "email": "kevin.ramos@example.com",
        "summary": "Database Engineer with 4 years of experience in PostgreSQL and MySQL operations, including schema migration, backup operations, and SQL troubleshooting in medium-scale environments.",
        "skills": [
            "PostgreSQL, MySQL, basic MS SQL Server",
            "SQL tuning and indexing",
            "Backup/restore operations and release support",
            "Linux, Bash, foundational Python",
            "Cloud exposure: AWS RDS, introductory Google Cloud SQL",
        ],
        "experience": [
            "Database Engineer, Northgrid Services (2022-2026): Supported 15 production databases and reduced slow-query backlog by 20%.",
            "Junior Data Ops Engineer, CityTel Labs (2020-2022): Performed DB health checks and backup verification with on-call support.",
        ],
        "education": "BS Information Technology, Ateneo de Manila University",
        "certifications": ["AWS Certified Cloud Practitioner"],
    },
    {
        "file": "resume_003_liza_cruz_senior_network_high.pdf",
        "name": "Liza Cruz",
        "role": "Senior Network Engineer",
        "candidate_id": "CAND-003",
        "location": "Makati, Philippines",
        "experience_years": "10 years",
        "phone": "+63 917 555 1003",
        "email": "liza.cruz@example.com",
        "summary": "Senior Network Engineer with 10 years in enterprise and telecom networks. Expert in BGP/OSPF/MPLS, network security, and high-severity incident handling with strong mentoring capability.",
        "skills": [
            "Routing and switching: BGP, OSPF, MPLS, VLAN, STP",
            "Cisco IOS/NX-OS, Juniper JUNOS, Arista EOS",
            "Firewall and security: Palo Alto, Fortinet, VPN, NAC",
            "Automation: Python, Ansible, Terraform",
            "Monitoring: SolarWinds, PRTG, Grafana, Wireshark",
        ],
        "experience": [
            "Lead Network Engineer, Pacific Telecom Core (2021-2026): Led data-center fabric upgrade increasing throughput by 38%.",
            "Senior Network Engineer, Harbor Enterprise Systems (2016-2021): Designed WAN segmentation across 60+ locations.",
        ],
        "education": "BS Electronics and Communications Engineering, De La Salle University",
        "certifications": ["Cisco CCNP Enterprise", "Juniper JNCIP-ENT"],
    },
    {
        "file": "resume_004_anne_lim_cloud_infra_high.pdf",
        "name": "Anne Lim",
        "role": "Cloud Infrastructure Engineer",
        "candidate_id": "CAND-004",
        "location": "Manila, Philippines",
        "experience_years": "7 years",
        "phone": "+63 917 555 1004",
        "email": "anne.lim@example.com",
        "summary": "Cloud Infrastructure Engineer focused on secure, scalable platforms across GCP and AWS. Strong in Kubernetes, Terraform, CI/CD, observability, and cloud cost optimization.",
        "skills": [
            "GCP, AWS",
            "Terraform, Ansible, CloudFormation",
            "Docker, Kubernetes (GKE/EKS)",
            "CI/CD: GitHub Actions, GitLab CI, Jenkins",
            "Python, Bash, Cloud Monitoring, Prometheus, Grafana",
        ],
        "experience": [
            "Senior Cloud Engineer, Nexa Digital Platforms (2022-2026): Reduced environment setup time by 80% using standardized IaC modules.",
            "Cloud Engineer, Manila App Labs (2019-2022): Designed CI/CD for microservices and improved release reliability.",
        ],
        "education": "BS Computer Engineering, University of Santo Tomas",
        "certifications": ["Google Professional Cloud Architect", "AWS Solutions Architect Associate"],
    },
    {
        "file": "resume_005_mark_tan_team_lead_high.pdf",
        "name": "Mark Tan",
        "role": "Engineering Team Lead",
        "candidate_id": "CAND-005",
        "location": "Manila, Philippines",
        "experience_years": "11 years",
        "phone": "+63 917 555 1005",
        "email": "mark.tan@example.com",
        "summary": "Engineering Team Lead with strong delivery and stakeholder management track record in telecom programs, while staying hands-on in architecture and engineering governance.",
        "skills": [
            "People leadership and mentoring (8-15 engineers)",
            "Roadmap planning, stakeholder management, risk control",
            "Architecture review and engineering standards",
            "Agile execution, incident governance",
            "Python, Java, SQL, cloud-native service architecture",
        ],
        "experience": [
            "Engineering Team Lead, Globe Partner Solutions (2020-2026): Improved on-time delivery from 72% to 93% across multi-squad roadmap.",
            "Senior Software Engineer, Enterprise Core Systems (2015-2020): Delivered reliability and performance improvements for customer workflows.",
        ],
        "education": "BS Computer Science, Mapua University",
        "certifications": ["PMI Agile Certified Practitioner", "Certified ScrumMaster"],
    },
    {
        "file": "resume_006_john_reyes_cloud_medium.pdf",
        "name": "John Reyes",
        "role": "Cloud/DevOps Engineer",
        "candidate_id": "CAND-006",
        "location": "Pasig, Philippines",
        "experience_years": "3 years",
        "phone": "+63 917 555 1006",
        "email": "john.reyes@example.com",
        "summary": "Cloud and DevOps Engineer with 3 years of experience in deployment automation, containerized workloads, and infrastructure support for growing product teams.",
        "skills": [
            "AWS (EC2, VPC, RDS), basic GCP",
            "Docker, Kubernetes (basic)",
            "Terraform (intermediate)",
            "GitHub Actions, Jenkins",
            "Bash and Python scripting",
        ],
        "experience": [
            "DevOps Engineer, Streamline Apps (2023-2026): Improved deployment success rate from 88% to 96% across 20+ services.",
            "Systems Engineer, Metro Systems (2021-2023): Managed Linux servers and release script automation.",
        ],
        "education": "BS Information Systems, University of Asia and the Pacific",
        "certifications": ["AWS Developer Associate"],
    },
    {
        "file": "resume_007_nina_gomez_software_medium.pdf",
        "name": "Nina Gomez",
        "role": "Software Engineer",
        "candidate_id": "CAND-007",
        "location": "Manila, Philippines",
        "experience_years": "5 years",
        "phone": "+63 917 555 1007",
        "email": "nina.gomez@example.com",
        "summary": "Backend Software Engineer with 5 years of experience building API platforms and service reliability features for high-volume digital products.",
        "skills": [
            "Python, FastAPI, Java, SQL",
            "PostgreSQL, Redis",
            "Docker and CI/CD pipelines",
            "Cloud Run, Cloud SQL",
            "Performance tuning and observability",
        ],
        "experience": [
            "Software Engineer, Digital Commerce Labs (2021-2026): Improved API latency by 30% through query tuning and caching.",
            "Junior Software Engineer, Finworks Manila (2019-2021): Built internal microservices and integration jobs.",
        ],
        "education": "BS Computer Science, University of the Philippines",
        "certifications": ["Google Associate Cloud Engineer"],
    },
    {
        "file": "resume_008_paolo_delacruz_network_cloud_medium.pdf",
        "name": "Paolo Dela Cruz",
        "role": "Network Engineer",
        "candidate_id": "CAND-008",
        "location": "Taguig, Philippines",
        "experience_years": "6 years",
        "phone": "+63 917 555 1008",
        "email": "paolo.delacruz@example.com",
        "summary": "Network Engineer with enterprise operations background and hybrid-cloud connectivity experience. Good troubleshooting depth and improving automation capability.",
        "skills": [
            "OSPF, BGP (intermediate), VLAN, ACL",
            "Cisco and Fortinet operations",
            "Network monitoring and incident response",
            "Basic Python and Ansible",
            "Site-to-site VPN and cloud connectivity",
        ],
        "experience": [
            "Network Engineer, EastBridge Networks (2020-2026): Reduced network MTTR by 22% through runbook improvements.",
            "NOC Engineer, NetOps PH (2018-2020): Performed real-time monitoring and escalation handling.",
        ],
        "education": "BS Information Technology, Adamson University",
        "certifications": ["Cisco CCNA", "Fortinet NSE 4"],
    },
    {
        "file": "resume_009_owen_lee_low_fit.pdf",
        "name": "Owen Lee",
        "role": "Sales Operations Specialist",
        "candidate_id": "CAND-009",
        "location": "Cebu, Philippines",
        "experience_years": "7 years",
        "phone": "+63 917 555 1009",
        "email": "owen.lee@example.com",
        "summary": "Sales operations specialist focused on CRM workflow optimization and pipeline analytics. Included as a low-fit control sample for engineering-role matching tests.",
        "skills": [
            "Salesforce administration",
            "Excel and BI dashboarding",
            "Forecasting and pipeline reporting",
            "Process governance and stakeholder communication",
        ],
        "experience": [
            "Senior Sales Ops Analyst, RetailConnect (2020-2026): Led CRM governance and monthly executive reporting.",
            "Sales Analyst, MarketGrid PH (2017-2020): Supported quota planning and regional forecast operations.",
        ],
        "education": "BS Marketing Management, University of San Carlos",
        "certifications": [],
    },
    {
        "file": "resume_010_priya_nair_devops_high_for_cloud.pdf",
        "name": "Priya Nair",
        "role": "Senior DevOps / Platform Engineer",
        "candidate_id": "CAND-010",
        "location": "Manila, Philippines",
        "experience_years": "9 years",
        "phone": "+63 917 555 1010",
        "email": "priya.nair@example.com",
        "summary": "Senior DevOps and Platform Engineer with deep cloud-native architecture experience in Kubernetes operations, IaC governance, and reliability engineering.",
        "skills": [
            "GCP, AWS, multi-account architecture",
            "Kubernetes platform engineering (GKE/EKS)",
            "Terraform and policy as code",
            "CI/CD governance and release engineering",
            "SLO-based reliability and observability",
        ],
        "experience": [
            "Principal DevOps Engineer, CoreScale Systems (2021-2026): Built internal developer platform adopted by 20+ squads.",
            "Senior DevOps Engineer, CloudSphere APAC (2017-2021): Standardized deployment pipelines and improved platform resilience.",
        ],
        "education": "MS Information Systems, De La Salle University",
        "certifications": ["Google Professional Cloud DevOps Engineer", "Certified Kubernetes Administrator (CKA)"],
    },
]


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Name",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#102A43"),
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Role",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#486581"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#102A43"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13,
            textColor=colors.HexColor("#243B53"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ResumeBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=12.8,
            leftIndent=10,
            textColor=colors.HexColor("#243B53"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Meta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334E68"),
        )
    )
    return styles


def hr_line(width):
    t = Table([[""]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (0, 0), 1, colors.HexColor("#BCCCDC")),
            ]
        )
    )
    return t


def create_resume_pdf(candidate, styles):
    out_path = OUT_DIR / candidate["file"]
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Resume - {candidate['name']}",
    )

    story = []
    story.append(Paragraph(candidate["name"], styles["Name"]))
    story.append(Paragraph(candidate["role"], styles["Role"]))

    meta_table = Table(
        [
            [
                f"<b>Candidate ID:</b> {candidate['candidate_id']}",
                f"<b>Experience:</b> {candidate['experience_years']}",
            ],
            [
                f"<b>Location:</b> {candidate['location']}",
                f"<b>Phone:</b> {candidate['phone']}",
            ],
            [
                f"<b>Email:</b> {candidate['email']}",
                "",
            ],
        ],
        colWidths=[85 * mm, 85 * mm],
        hAlign="LEFT",
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334E68")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 4))
    story.append(hr_line(178 * mm))

    story.append(Paragraph("Professional Summary", styles["Section"]))
    story.append(Paragraph(candidate["summary"], styles["Body"]))

    story.append(Paragraph("Core Skills", styles["Section"]))
    for item in candidate["skills"]:
        story.append(Paragraph(f"- {item}", styles["ResumeBullet"]))

    story.append(Paragraph("Work Experience", styles["Section"]))
    for item in candidate["experience"]:
        story.append(Paragraph(f"- {item}", styles["ResumeBullet"]))

    story.append(Paragraph("Education", styles["Section"]))
    story.append(Paragraph(candidate["education"], styles["Body"]))

    if candidate["certifications"]:
        story.append(Paragraph("Certifications", styles["Section"]))
        for cert in candidate["certifications"]:
            story.append(Paragraph(f"- {cert}", styles["ResumeBullet"]))

    story.append(Spacer(1, 10))
    story.append(hr_line(178 * mm))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Confidential candidate profile for hiring pipeline evaluation.", styles["Meta"]))

    doc.build(story)


def main():
    styles = build_styles()
    for candidate in CANDIDATES:
        create_resume_pdf(candidate, styles)
    print(f"Generated {len(CANDIDATES)} PDF resumes at {OUT_DIR}")


if __name__ == "__main__":
    main()
