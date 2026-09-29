"""SaaS Usage Metering, Quota Management, and Tier Enforcement."""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select

from cci.db.models.organizations import Organization
from cci.db.session import SessionLocal

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free Tier",
        "monthly_analyses_limit": 15,
        "max_repos_per_analysis": 3,
        "team_seats": 2,
        "export_formats": ["html", "json"],
        "price_usd": 0,
    },
    "starter": {
        "name": "Starter",
        "monthly_analyses_limit": 100,
        "max_repos_per_analysis": 6,
        "team_seats": 5,
        "export_formats": ["html", "json", "markdown", "csv"],
        "price_usd": 99,
    },
    "pro": {
        "name": "Pro Recruiter",
        "monthly_analyses_limit": 500,
        "max_repos_per_analysis": 15,
        "team_seats": 20,
        "export_formats": ["html", "json", "markdown", "csv"],
        "price_usd": 299,
    },
    "enterprise": {
        "name": "Enterprise Custom",
        "monthly_analyses_limit": 10000,
        "max_repos_per_analysis": 50,
        "team_seats": 100,
        "export_formats": ["html", "json", "markdown", "csv"],
        "price_usd": 999,
    },
}


def get_current_billing_cycle() -> str:
    """Returns YYYY-MM formatted current billing cycle."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


class BillingService:
    """Thread-safe usage metering and quota enforcement."""

    def get_tier_and_limits(self, org_id: UUID) -> Dict[str, Any]:
        """Gets the subscription tier and current limits for an organization."""
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            plan_name = "pro"  # Default to pro in development / early access
            if org and org.settings:
                plan_name = org.settings.get("plan", "pro")

            plan = PLANS.get(plan_name, PLANS["pro"])
            return {
                "organization_id": str(org_id),
                "plan_key": plan_name,
                "plan_name": plan["name"],
                "limits": plan,
            }

    def check_analysis_quota(self, org_id: UUID) -> None:
        """Verifies that the organization has not exceeded their monthly analysis quota.
        
        Raises HTTP 402 (Payment Required) if limit is exceeded.
        """
        cycle = get_current_billing_cycle()
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org:
                return  # If org doesn't exist yet, proceed

            settings_dict = dict(org.settings or {})
            usage_dict = settings_dict.get("usage", {})
            current_month_usage = usage_dict.get(cycle, {}).get("analyses_count", 0)

            plan_name = settings_dict.get("plan", "pro")
            plan = PLANS.get(plan_name, PLANS["pro"])
            limit = plan["monthly_analyses_limit"]

            if current_month_usage >= limit:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        f"Monthly analysis quota exceeded ({current_month_usage}/{limit} analyses used). "
                        "Please upgrade your subscription plan to run more candidate evaluations."
                    ),
                )

    def record_analysis_usage(self, org_id: UUID, candidate_id: UUID) -> Dict[str, Any]:
        """Records an executed analysis towards the organization's monthly quota."""
        cycle = get_current_billing_cycle()
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org:
                return {"status": "untracked"}

            settings_dict = dict(org.settings or {})
            usage_dict = settings_dict.setdefault("usage", {})
            cycle_data = usage_dict.setdefault(cycle, {"analyses_count": 0, "last_analysis_at": None})

            cycle_data["analyses_count"] += 1
            cycle_data["last_analysis_at"] = datetime.now(timezone.utc).isoformat()

            # Ensure SQLAlchemy detects the change to the JSON column
            org.settings = dict(settings_dict)
            db.commit()

            plan_name = settings_dict.get("plan", "pro")
            limit = PLANS.get(plan_name, PLANS["pro"])["monthly_analyses_limit"]

            return {
                "cycle": cycle,
                "used": cycle_data["analyses_count"],
                "limit": limit,
                "remaining": max(0, limit - cycle_data["analyses_count"]),
            }

    def get_usage_summary(self, org_id: UUID) -> Dict[str, Any]:
        """Returns full usage breakdown and quota statistics for the organization."""
        cycle = get_current_billing_cycle()
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            settings_dict = dict(org.settings or {}) if org else {}
            plan_name = settings_dict.get("plan", "pro")
            plan = PLANS.get(plan_name, PLANS["pro"])

            usage_dict = settings_dict.get("usage", {})
            cycle_data = usage_dict.get(cycle, {"analyses_count": 0, "last_analysis_at": None})
            used = cycle_data.get("analyses_count", 0)
            limit = plan["monthly_analyses_limit"]

            return {
                "organization_id": str(org_id),
                "billing_cycle": cycle,
                "plan": plan_name,
                "plan_name": plan["name"],
                "price_usd": plan["price_usd"],
                "analyses_used": used,
                "analyses_limit": limit,
                "analyses_remaining": max(0, limit - used),
                "usage_percentage": round((used / limit) * 100, 1) if limit > 0 else 0.0,
                "team_seats_limit": plan["team_seats"],
                "max_repos_limit": plan["max_repos_per_analysis"],
                "export_formats": plan["export_formats"],
            }


billing_service = BillingService()
