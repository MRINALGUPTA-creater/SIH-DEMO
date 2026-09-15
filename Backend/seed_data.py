import os
import sys
import uuid
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from vector_db import QdrantStorage
from data_loader import embed_texts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_data")

BIS_DOCUMENT_CORPUS = [
    {
        "source": "IS 13252 (Part 1):2010 - Information Technology Equipment Safety",
        "text": (
            "Indian Standard IS 13252 (Part 1) covers general safety requirements for Information Technology Equipment, "
            "including Smart Televisions, LED/LCD displays, computing apparatus, and visual display terminals. "
            "It is mandatory under the Compulsory Registration Scheme (CRS) administered by the Bureau of Indian Standards (BIS). "
            "Key compliance requirements include electrical safety testing (dielectric strength, insulation resistance, "
            "leakage current), protection against electric shock, resistance to fire (flammability classification UL94/V-0), "
            "and official BIS Standard Mark labelling with valid Registration number (R-number) and portal URL."
        )
    },
    {
        "source": "IS 616:2017 - Audio, Video and Similar Electronic Apparatus Safety",
        "text": (
            "IS 616 establishes safety requirements for audio, video, and similar electronic apparatus intended for domestic "
            "and commercial entertainment. This covers television receivers, monitors, power adapters, and sound systems. "
            "Products must undergo mechanical strength tests, thermal endurance tests, and abnormal operating condition tests. "
            "Manufacturers must ensure adequate creepage distances and clearances around high-voltage power boards."
        )
    },
    {
        "source": "IS 4250:2020 - Domestic Electric Food Mixers, Grinders and Kettles",
        "text": (
            "IS 4250 specifies requirements for domestic electric appliances including food mixers, grinders, and electric kettles. "
            "Certification is governed under BIS Scheme I (ISI Marking Scheme). "
            "Essential parameters include rated capacity marking, nominal power and voltage markings (230 V, single phase AC), "
            "dielectric withstand test at 1500 V, thermal cut-out safety operation during dry-boil conditions, and factory quality-control protocols."
        )
    },
    {
        "source": "IS 302-2-15:2009 - Safety of Household Electrical Appliances - Heating Liquids",
        "text": (
            "IS 302-2-15 deals with the safety of electric appliances for heating liquids for household and similar purposes, "
            "such as electric kettles, coffee makers, and immersion heaters. "
            "It requires automatic shutoff mechanisms when liquid boils or evaporates, protection against accidental scalding, "
            "cord anchorage security, and moisture resistance under humid conditions. "
            "Compliance evidence requires third-party accredited laboratory test reports and routine factory inspection records."
        )
    },
    {
        "source": "BIS Scheme I - ISI Product Certification Guidelines",
        "text": (
            "The ISI Mark Scheme (Scheme I of BIS Conformity Assessment Regulations) involves rigorous factory assessment "
            "and independent laboratory sample testing. Manufacturers must maintain in-house testing facilities, a qualified quality control team, "
            "and approved Schemes of Inspection and Testing (SIT). After successful audit and test compliance, a CM/L licence is granted."
        )
    },
    {
        "source": "BIS Compulsory Registration Scheme (CRS) Workflow",
        "text": (
            "Under the BIS Compulsory Registration Scheme (CRS), electronics and IT goods (such as smart TVs, laptop computers, and power banks) "
            "must be tested in BIS-recognized laboratories in India. The manufacturer then submits test reports along with an undertaking on the "
            "BIS portal to obtain a unique Registration Number (R-XXXXXXXX) and apply the standard CRS e-label on the device and packaging."
        )
    },
]


def seed_vector_db():
    logger.info("Seeding Qdrant vector database with BIS standards knowledge...")
    storage = QdrantStorage()
    chunks = [doc["text"] for doc in BIS_DOCUMENT_CORPUS]
    sources = [doc["source"] for doc in BIS_DOCUMENT_CORPUS]

    logger.info(f"Generating embeddings for {len(chunks)} knowledge items...")
    vectors = embed_texts(chunks)

    ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"bis_knowledge:{i}")) for i in range(len(chunks))]
    payloads = [{"source": sources[i], "text": chunks[i]} for i in range(len(chunks))]

    storage.upsert(ids, vectors, payloads)
    logger.info(f"Successfully seeded {len(chunks)} items into Qdrant collection '{storage.collection_name}'.")


def main():
    logger.info("Initializing Database...")
    db = DatabaseManager()
    stats = db.get_dashboard_statistics()
    logger.info(f"Database statistics: {stats}")

    seed_vector_db()
    logger.info("All seed data initialization complete!")


if __name__ == "__main__":
    main()
