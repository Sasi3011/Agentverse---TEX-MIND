from datetime import datetime
from typing import List, Dict, Any, Tuple

# Tamil Nadu Registry: Each facility owns its own exact certificate and status
CERTIFICATE_REGISTRY = {
    "GOTS-TN-101": {"issuer": "Global Organic Textile Standard", "entity": "Kongu Organic Cotton Farmers Co-op", "location": "Pollachi", "status": "Valid", "scope": "Farm"},
    "GOTS-TN-102": {"issuer": "Global Organic Textile Standard", "entity": "Pollachi Sustainable Farms", "location": "Pollachi", "status": "Valid", "scope": "Farm"},
    "GOTS-TN-103": {"issuer": "Global Organic Textile Standard", "entity": "Amaravathi Organic Cotton Collective", "location": "Udumalpet", "status": "Valid", "scope": "Farm"},
    "GOTS-TN-201": {"issuer": "Global Organic Textile Standard", "entity": "Coimbatore Modern Ginning Works", "location": "Coimbatore", "status": "Valid", "scope": "Ginning"},
    "GOTS-TN-202": {"issuer": "Global Organic Textile Standard", "entity": "Tiruppur Cotton Ginning Mills", "location": "Tiruppur", "status": "Valid", "scope": "Ginning"},
    "OEKO-TN-301": {"issuer": "OEKO-TEX Association", "entity": "Lakshmi Mills Co-op Ltd", "location": "Coimbatore", "status": "Valid", "scope": "Spinning"},
    "OEKO-TN-302": {"issuer": "OEKO-TEX Association", "entity": "KPR Mill Spinning Division", "location": "Tiruppur", "status": "Valid", "scope": "Spinning"},
    "OEKO-TN-401": {"issuer": "OEKO-TEX Association", "entity": "Tiruppur Knitwear & Weaving Park", "location": "Tiruppur", "status": "Valid", "scope": "Weaving"},
    "GOTS-TN-501": {"issuer": "Global Organic Textile Standard", "entity": "ZLD Dyeing Park", "location": "Tiruppur", "status": "Valid", "scope": "Dyeing"},
    
    # Invalid / Expired / Revoked / Problematic Certificates for testing
    "GOTS-EXPIRED-01": {"issuer": "Global Organic Textile Standard", "entity": "Old Kovai Dye Works", "location": "Coimbatore", "status": "Expired", "scope": "Dyeing"},
    "GOTS-REVOKED-99": {"issuer": "Global Organic Textile Standard", "entity": "Cauvery Delta Planters", "location": "Erode", "status": "Revoked", "scope": "Farm"}
}

REQUIRED_STAGES = ["farm", "ginning", "spinning", "weaving", "dyeing"]

def validate_batch_custody(
    custody_log: List[Dict[str, Any]], 
    total_distance_km: float, 
    transit_hours: float, 
    raw_cotton_kg: float, 
    finished_fabric_kg: float
) -> Dict[str, Any]:
    
    audit_warnings = []
    
    # 1. Stage Completeness Verification
    logged_stages = set([entry.get("stage", "").lower() for entry in custody_log])
    present_stages_count = sum(1 for stage in REQUIRED_STAGES if stage in logged_stages)
    completeness_score = int((present_stages_count / 5.0) * 100)
    missing_stages = [stage for stage in REQUIRED_STAGES if stage not in logged_stages]
    
    if missing_stages:
        audit_warnings.append(f"Missing required supply chain stages: {', '.join(missing_stages)}")

    # 2. Transit Speed Verification (Speed = Distance / Time)
    hours = max(transit_hours, 0.01)
    transit_speed = round(total_distance_km / hours, 1)
    if transit_speed > 90.0:
        transit_status = "Suspicious Fast (Unfeasible)"
        audit_warnings.append(f"Unfeasible transit speed detected: {transit_speed} km/h across {total_distance_km} km in {transit_hours} hrs")
    elif transit_speed < 5.0 and total_distance_km > 20:
        transit_status = "Delayed Transit"
        audit_warnings.append(f"Excessive transit delay: {transit_speed} km/h")
    else:
        transit_status = "Feasible Normal"

    # 3. Mass Yield Verification (Output Mass / Input Mass)
    if raw_cotton_kg <= 0:
        mass_yield = 0.0
        mass_status = "Invalid Input Mass"
        audit_warnings.append("Raw cotton input mass must be greater than 0 kg")
    else:
        mass_yield = round(finished_fabric_kg / raw_cotton_kg, 2)
        if mass_yield < 0.70 or mass_yield > 0.95:
            mass_status = "Unfeasible Yield Anomaly"
            audit_warnings.append(f"Mass yield ratio of {mass_yield} (output {finished_fabric_kg}kg / input {raw_cotton_kg}kg) outside valid 0.70-0.95 range")
        else:
            mass_status = "Valid Production Yield"

    # 4. Certificate Validation per Facility
    stage_cert_details = []
    has_cert_issue = False

    for entry in custody_log:
        stage = entry.get("stage", "").capitalize()
        entity = entry.get("entity", "").strip()
        cert_ref = entry.get("cert_ref", "").strip() if entry.get("cert_ref") else None

        if not cert_ref:
            stage_cert_details.append({
                "stage": stage,
                "entity": entity,
                "cert_ref": "None",
                "status": "Uncertified",
                "issue": "No certificate provided"
            })
            continue

        if cert_ref not in CERTIFICATE_REGISTRY:
            has_cert_issue = True
            audit_warnings.append(f"Unknown Certificate: '{cert_ref}' for {entity}")
            stage_cert_details.append({
                "stage": stage,
                "entity": entity,
                "cert_ref": cert_ref,
                "status": "Unknown",
                "issue": "Unknown Certificate"
            })
        else:
            reg_info = CERTIFICATE_REGISTRY[cert_ref]
            reg_status = reg_info["status"]
            reg_entity = reg_info["entity"]

            if reg_status == "Expired":
                has_cert_issue = True
                audit_warnings.append(f"Expired Certificate: '{cert_ref}' for {entity}")
                stage_cert_details.append({
                    "stage": stage,
                    "entity": entity,
                    "cert_ref": cert_ref,
                    "status": "Expired",
                    "issue": "Expired Certificate"
                })
            elif reg_status == "Revoked":
                has_cert_issue = True
                audit_warnings.append(f"Revoked Certificate: '{cert_ref}' for {entity}")
                stage_cert_details.append({
                    "stage": stage,
                    "entity": entity,
                    "cert_ref": cert_ref,
                    "status": "Revoked",
                    "issue": "Revoked Certificate"
                })
            elif reg_entity.lower() != entity.lower():
                has_cert_issue = True
                audit_warnings.append(f"Entity Mismatch: Certificate '{cert_ref}' belongs to '{reg_entity}', not '{entity}'")
                stage_cert_details.append({
                    "stage": stage,
                    "entity": entity,
                    "cert_ref": cert_ref,
                    "status": "Mismatch",
                    "issue": "Entity Mismatch"
                })
            else:
                stage_cert_details.append({
                    "stage": stage,
                    "entity": entity,
                    "cert_ref": cert_ref,
                    "status": "Valid",
                    "issue": "None"
                })

    overall_cert_status = "FAILED" if has_cert_issue else ("PASSED" if present_stages_count == 5 else "INCOMPLETE")

    return {
        "completeness_score": completeness_score,
        "present_stages_count": present_stages_count,
        "missing_stages": missing_stages,
        "transit_speed": transit_speed,
        "transit_status": transit_status,
        "mass_yield": mass_yield,
        "mass_status": mass_status,
        "stage_cert_details": stage_cert_details,
        "overall_cert_status": overall_cert_status,
        "has_cert_issue": has_cert_issue,
        "audit_warnings": audit_warnings
    }
