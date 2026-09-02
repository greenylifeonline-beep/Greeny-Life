"""Read-only provider adapters. Catalog facts are not claimed as live account remaining quota."""

from __future__ import annotations

from typing import Any

from .contract import CAPABILITIES
from .schema import (
    UNKNOWN,
    accelerator_resource,
    account,
    compute_resource,
    credit,
    price,
    provider,
    quota,
    region,
    service,
    storage_resource,
    utc,
)

CATALOG_AT = "2026-08-27T00:00:00+00:00"
CATALOG_SOURCE = "PUBLIC_CATALOG_NOT_ACCOUNT_REMAINING"


class ReadOnlyAdapter:
    mutating_forbidden = True

    def capabilities(self) -> tuple[str, ...]:
        return CAPABILITIES

    def plan_placement(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"STATUS": "PLAN_ONLY", "request": request, "MUTATION": False}

    def discover_usage(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def health(self, account_id: str) -> dict[str, Any]:
        return {
            "account_id": account_id,
            "status": "UNKNOWN",
            "UNOBSERVED_NE_ABSENT": True,
            "probe": "NOT_RUN",
        }


class OracleAdapter(ReadOnlyAdapter):
    provider_id = "ORACLE_CLOUD"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="public_cloud",
            display_name="Oracle Cloud Infrastructure",
            api_type="oci",
            cli_type="oci",
            supports_gpu=True,
            supports_serverless=True,
            supports_model_hosting=False,
            supports_persistent_workers=True,
            supports_api_probe=True,
            supports_cli_probe=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="ORACLE_01",
                provider_id=self.provider_id,
                account_alias="ORACLE_01",
                owner_alias="C1",
                credential_ref="env:OCI_CONFIG_ORACLE_01",
                default_region="eu-stockholm-1",
                available_regions=["eu-stockholm-1"],
                provenance_refs=[
                    "RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:oracle-primary",
                    ".ai-os/learning/FREE-RESOURCES.json",
                ],
                status="DECLARED",
            )
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="eu-stockholm-1", provider_id=self.provider_id, display_name="Sweden Central")]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return [
            compute_resource(
                resource_id=f"{account_id}:ampere-a1-catalog",
                provider_id=self.provider_id,
                account_id=account_id,
                region="eu-stockholm-1",
                instance_type="VM.Standard.A1.Flex",
                architecture="aarch64",
                persistent=True,
                ephemeral=False,
                public_endpoint_allowed=True,
                price_per_hour=UNKNOWN,
                available_capacity=UNKNOWN,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return [
            accelerator_resource(
                resource_id=f"{account_id}:gpu-catalog",
                provider_id=self.provider_id,
                account_id=account_id,
                region="eu-stockholm-1",
                gpu_vendor=UNKNOWN,
                gpu_model=UNKNOWN,
                available=UNKNOWN,
            )
        ]

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        rows = []
        for st, persist, model in (
            ("persistent_block", True, False),
            ("object_storage", True, True),
            ("backup_storage", True, False),
            ("archive_storage", True, False),
            ("snapshot_storage", True, False),
        ):
            rows.append(
                storage_resource(
                    storage_id=f"{account_id}:{st}",
                    provider_id=self.provider_id,
                    account_id=account_id,
                    region="eu-stockholm-1",
                    storage_type=st,
                    persistent=persist,
                    model_weights_suitable=model,
                    checkpoint_suitable=model,
                    artifact_suitable=True,
                    backup_suitable=st in {"backup_storage", "object_storage", "archive_storage"},
                    capacity_total_gb=UNKNOWN,
                    capacity_free_gb=UNKNOWN,
                )
            )
        return rows

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        cats = [
            ("compute", "VM", True, True),
            ("object-storage", "OBJECT_STORAGE", True, True),
            ("block-storage", "BLOCK_STORAGE", True, True),
            ("functions", "FUNCTIONS", False, True),
            ("oke", "KUBERNETES", False, True),
            ("adb", "SQL", False, True),
            ("queue", "QUEUE", False, True),
            ("logging", "LOGGING", True, True),
            ("iam", "IAM", True, True),
            ("vault", "SECRETS", True, True),
        ]
        out = []
        for sid, cat, enabled, avail in cats:
            out.append(
                service(
                    service_id=f"{account_id}:{sid}",
                    service_name=sid,
                    category=cat,
                    provider_id=self.provider_id,
                    account_id=account_id,
                    enabled=enabled,
                    available=avail,
                    quota_available=UNKNOWN,
                    raios_value="CONTROL_OR_STORAGE_CANDIDATE" if cat in {"VM", "OBJECT_STORAGE"} else UNKNOWN,
                )
            )
        return out

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return [
            quota(
                quota_id=f"{account_id}:a1-ocpu",
                provider_id=self.provider_id,
                account_id=account_id,
                service_id=f"{account_id}:compute",
                resource_type="ocpu",
                limit=UNKNOWN,
                used=UNKNOWN,
                remaining=UNKNOWN,
                unit="OCPU",
            )
        ]

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return [
            credit(
                credit_id=f"{account_id}:trial-or-paid",
                provider_id=self.provider_id,
                account_id=account_id,
                remaining_value=UNKNOWN,
                currency="USD",
            )
        ]

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return [
            price(
                price_id=f"{account_id}:object-gb-month",
                kind="CATALOG_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                region="eu-stockholm-1",
                resource_type="object_storage",
                amount=UNKNOWN,
                pricing_unit="GB_MONTH",
                source=CATALOG_SOURCE,
                observed_at=CATALOG_AT,
            )
        ]


class KaggleAdapter(ReadOnlyAdapter):
    provider_id = "KAGGLE"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="notebook_platform",
            display_name="Kaggle",
            api_type="kaggle-api",
            cli_type="kaggle",
            supports_gpu=True,
            supports_notebooks=True,
            supports_storage=True,
            supports_persistent_workers=False,
            supports_cli_probe=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="KAGGLE_C1",
                provider_id=self.provider_id,
                account_alias="KAGGLE_C1",
                owner_alias="C1",
                credential_ref="existing-receipt:KAGGLE-AUTHENTICATED-READ-RECEIPT",
                provenance_refs=[
                    "RAIOS/V9/cloud/nomadic/worker_contract.py:KAGGLE_A",
                    "RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:kaggle-a:greenylife",
                    ".ai-os/reports/master-estate-census/RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z/cloud/kaggle/KAGGLE-BINDING.json",
                ],
                status="DECLARED",
            ),
            account(
                account_id="KAGGLE_PARTNER",
                provider_id=self.provider_id,
                account_alias="KAGGLE_PARTNER",
                owner_alias="PARTNER",
                credential_ref="env:KAGGLE_CONFIG_B",
                provenance_refs=["RAIOS/V9/cloud/nomadic/worker_contract.py:KAGGLE_B"],
                status="DECLARED",
            ),
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="kaggle-hosted", provider_id=self.provider_id)]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return [
            compute_resource(
                resource_id=f"{account_id}:notebook-session",
                provider_id=self.provider_id,
                account_id=account_id,
                region="kaggle-hosted",
                instance_type="kaggle-notebook",
                persistent=False,
                ephemeral=True,
                max_runtime="SESSION_LIMIT",
                background_process_allowed=False,
                public_endpoint_allowed=False,
                available_capacity=UNKNOWN,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return [
            accelerator_resource(
                resource_id=f"{account_id}:gpu-p100-catalog",
                provider_id=self.provider_id,
                account_id=account_id,
                accelerator_type="GPU",
                gpu_vendor="NVIDIA",
                gpu_model="P100",
                gpu_count=1,
                gpu_vram_gb=16,
                weekly_quota=UNKNOWN,
                available=UNKNOWN,
                free_quota=UNKNOWN,
            ),
            accelerator_resource(
                resource_id=f"{account_id}:gpu-t4-catalog",
                provider_id=self.provider_id,
                account_id=account_id,
                gpu_vendor="NVIDIA",
                gpu_model="T4",
                gpu_count=2,
                gpu_vram_gb=16,
                available=UNKNOWN,
            ),
            accelerator_resource(
                resource_id=f"{account_id}:tpu-catalog",
                provider_id=self.provider_id,
                account_id=account_id,
                accelerator_type="TPU",
                tpu_type=UNKNOWN,
                available=UNKNOWN,
            ),
        ]

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return [
            storage_resource(
                storage_id=f"{account_id}:dataset_storage",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="dataset_storage",
                persistent=True,
                model_weights_suitable=True,
                artifact_suitable=True,
                capacity_total_gb=UNKNOWN,
                capacity_free_gb=UNKNOWN,
            ),
            storage_resource(
                storage_id=f"{account_id}:notebook_storage",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="notebook_storage",
                persistent=False,
                capacity_total_gb=UNKNOWN,
                capacity_free_gb=UNKNOWN,
            ),
            storage_resource(
                storage_id=f"{account_id}:model_storage",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="model_storage",
                persistent=True,
                model_weights_suitable=True,
                capacity_total_gb=UNKNOWN,
                capacity_free_gb=UNKNOWN,
            ),
            storage_resource(
                storage_id=f"{account_id}:artifact_storage",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="artifact_storage",
                persistent=True,
                artifact_suitable=True,
                capacity_total_gb=UNKNOWN,
                capacity_free_gb=UNKNOWN,
            ),
        ]

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return [
            service(
                service_id=f"{account_id}:notebook",
                service_name="notebooks",
                category="GPU_NOTEBOOK",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                quota_available=UNKNOWN,
                raios_value="GPU_BURST",
            ),
            service(
                service_id=f"{account_id}:datasets",
                service_name="datasets",
                category="OBJECT_STORAGE",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                quota_available=UNKNOWN,
                raios_value="MODEL_STORAGE",
            ),
            service(
                service_id=f"{account_id}:models",
                service_name="models",
                category="MODEL_REGISTRY",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                quota_available=UNKNOWN,
            ),
        ]

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return [
            quota(
                quota_id=f"{account_id}:gpu-weekly",
                provider_id=self.provider_id,
                account_id=account_id,
                service_id=f"{account_id}:notebook",
                resource_type="gpu_hours",
                remaining=UNKNOWN,
                unit="hours",
                reset_period="WEEKLY",
            )
        ]

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return [
            price(
                price_id=f"{account_id}:gpu-free-tier",
                kind="FREE_TIER_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                resource_type="gpu",
                amount=0,
                pricing_unit="HOUR",
                source=CATALOG_SOURCE,
                observed_at=CATALOG_AT,
            )
        ]


class LightningAdapter(ReadOnlyAdapter):
    provider_id = "LIGHTNING"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="studio_cloud",
            display_name="Lightning AI",
            api_type="lightning",
            cli_type="lightning",
            supports_gpu=True,
            supports_notebooks=True,
            supports_persistent_workers=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="LIGHTNING_01",
                provider_id=self.provider_id,
                account_alias="LIGHTNING_01",
                owner_alias="C1",
                credential_ref="env:LIGHTNING_USER_ID",
                provenance_refs=[
                    "RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:lightning:greenylifeonline-org"
                ],
            ),
            account(
                account_id="LIGHTNING_PARTNER",
                provider_id=self.provider_id,
                account_alias="LIGHTNING_PARTNER",
                owner_alias="PARTNER",
                credential_ref="file-ref:%USERPROFILE%/.raios/accounts/lightning/partner/model-api.json",
                provenance_refs=[
                    "RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:lightning:mariamnhend1-org"
                ],
            ),
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="lightning-default", provider_id=self.provider_id)]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return []
        return [
            compute_resource(
                resource_id=f"{account_id}:studio",
                provider_id=self.provider_id,
                account_id=account_id,
                instance_type="studio",
                persistent=True,
                ephemeral=False,
                available_capacity=UNKNOWN,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return []
        return [
            accelerator_resource(
                resource_id=f"{account_id}:studio-gpu",
                provider_id=self.provider_id,
                account_id=account_id,
                gpu_model=UNKNOWN,
                gpu_vram_gb=UNKNOWN,
                available=UNKNOWN,
            )
        ]

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return []
        return [
            storage_resource(
                storage_id=f"{account_id}:file_storage",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="file_storage",
                persistent=True,
                model_weights_suitable=True,
                checkpoint_suitable=True,
            )
        ]

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return [
                service(
                    service_id=f"{account_id}:model-api",
                    service_name="model-api",
                    category="INFERENCE_ENDPOINT",
                    provider_id=self.provider_id,
                    account_id=account_id,
                    enabled=True,
                    available=True,
                    quota_available=UNKNOWN,
                )
            ]
        return [
            service(
                service_id=f"{account_id}:studio",
                service_name="studios",
                category="DEV_ENVIRONMENT",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                quota_available=UNKNOWN,
            )
        ]

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return []
        return [
            credit(
                credit_id=f"{account_id}:org-credits",
                provider_id=self.provider_id,
                account_id=account_id,
                original_value=UNKNOWN,
                remaining_value=UNKNOWN,
                currency="USD",
                restrictions=["CURRENT_BALANCE_NOT_PROVEN"],
            )
        ]

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        if account_id == "LIGHTNING_PARTNER":
            return [
                price(
                    price_id=f"{account_id}:model-api-unproven",
                    kind="CATALOG_PRICE",
                    provider_id=self.provider_id,
                    account_id=account_id,
                    resource_type="inference_tokens",
                    amount=UNKNOWN,
                    pricing_unit="MILLION_UNITS",
                    source=CATALOG_SOURCE,
                    observed_at=CATALOG_AT,
                )
            ]
        return [
            price(
                price_id=f"{account_id}:gpu-hour",
                kind="CATALOG_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                resource_type="gpu",
                amount=UNKNOWN,
                pricing_unit="HOUR",
                source=CATALOG_SOURCE,
                observed_at=CATALOG_AT,
            )
        ]


class ColabAdapter(ReadOnlyAdapter):
    provider_id = "COLAB"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="notebook_platform",
            display_name="Google Colab",
            supports_gpu=True,
            supports_notebooks=True,
            supports_persistent_workers=False,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="COLAB_01",
                provider_id=self.provider_id,
                account_alias="COLAB_01",
                owner_alias="C1",
                credential_ref="env:COLAB_SESSION_REF",
                provenance_refs=["RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:colab"],
                status="DECLARED",
            )
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="colab-hosted", provider_id=self.provider_id)]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return [
            compute_resource(
                resource_id=f"{account_id}:runtime",
                provider_id=self.provider_id,
                account_id=account_id,
                persistent=False,
                ephemeral=True,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return [
            accelerator_resource(
                resource_id=f"{account_id}:colab-gpu",
                provider_id=self.provider_id,
                account_id=account_id,
                gpu_model=UNKNOWN,
                gpu_vram_gb=UNKNOWN,
                available=UNKNOWN,
            )
        ]

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return [
            storage_resource(
                storage_id=f"{account_id}:ephemeral_disk",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="ephemeral_disk",
                persistent=False,
            )
        ]

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return [
            service(
                service_id=f"{account_id}:notebook",
                service_name="colab",
                category="GPU_NOTEBOOK",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=False,
                available=True,
                quota_available=UNKNOWN,
            )
        ]

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return [
            price(
                price_id=f"{account_id}:free-tier",
                kind="FREE_TIER_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                resource_type="runtime",
                amount=0,
                pricing_unit="HOUR",
                source=CATALOG_SOURCE,
                observed_at=CATALOG_AT,
            )
        ]


class ModalAdapter(ReadOnlyAdapter):
    provider_id = "MODAL"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="serverless_compute",
            display_name="Modal",
            api_type="modal",
            cli_type="modal",
            supports_gpu=True,
            supports_serverless=True,
            supports_model_hosting=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="MODAL_01",
                provider_id=self.provider_id,
                account_alias="MODAL_01",
                owner_alias="C1",
                credential_ref="file-ref:%USERPROFILE%/.modal.toml#RAIOS_C1",
                provenance_refs=["RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:modal"],
            ),
            account(
                account_id="MODAL_PARTNER",
                provider_id=self.provider_id,
                account_alias="MODAL_PARTNER",
                owner_alias="PARTNER",
                credential_ref="file-ref:%USERPROFILE%/.modal.toml#RAIOS_PARTNER",
                provenance_refs=["RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py:modal-partner"],
            ),
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="modal-global", provider_id=self.provider_id)]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return [
            compute_resource(
                resource_id=f"{account_id}:function",
                provider_id=self.provider_id,
                account_id=account_id,
                instance_type="modal-function",
                persistent=False,
                ephemeral=True,
                container_allowed=True,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return [
            accelerator_resource(
                resource_id=f"{account_id}:modal-gpu",
                provider_id=self.provider_id,
                account_id=account_id,
                gpu_model=UNKNOWN,
                gpu_vram_gb=UNKNOWN,
                credit_eligible=True,
            )
        ]

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return [
            storage_resource(
                storage_id=f"{account_id}:volume",
                provider_id=self.provider_id,
                account_id=account_id,
                storage_type="file_storage",
                persistent=True,
                model_weights_suitable=True,
            )
        ]

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return [
            service(
                service_id=f"{account_id}:functions",
                service_name="functions",
                category="SERVERLESS",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                quota_available=UNKNOWN,
                public_endpoint=True,
            )
        ]

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return [
            credit(
                credit_id=f"{account_id}:workspace-credits",
                provider_id=self.provider_id,
                account_id=account_id,
                remaining_value=UNKNOWN,
            )
        ]

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return [
            price(
                price_id=f"{account_id}:gpu-hour",
                kind="CATALOG_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                resource_type="gpu",
                amount=UNKNOWN,
                pricing_unit="HOUR",
                source=CATALOG_SOURCE,
                observed_at=CATALOG_AT,
            )
        ]


class GenericSshAdapter(ReadOnlyAdapter):
    provider_id = "GENERIC_SSH"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="generic",
            display_name="Generic SSH host",
            supports_persistent_workers=True,
            supports_gpu=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return []

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return []


class GenericHttpInferenceAdapter(ReadOnlyAdapter):
    provider_id = "GENERIC_HTTP_INFERENCE"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="generic",
            display_name="Generic HTTP inference",
            api_type="http",
            supports_model_hosting=True,
            supports_api_probe=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return [
            account(
                account_id="LOCAL_AG",
                provider_id=self.provider_id,
                account_alias="LOCAL_AG",
                owner_alias="C1",
                credential_ref="existing:OWNER_LOCAL_CONTROL_PLANE",
                provenance_refs=[".ai-os/learning/FREE-RESOURCES.json:founder-laptop"],
                status="DECLARED",
            )
        ]

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return [region(region_id="local", provider_id=self.provider_id)]

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return [
            compute_resource(
                resource_id=f"{account_id}:control-node",
                provider_id=self.provider_id,
                account_id=account_id,
                region="local",
                persistent=True,
                ephemeral=False,
                public_endpoint_allowed=False,
                private_endpoint_allowed=True,
            )
        ]

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return [
            storage_resource(
                storage_id=f"{account_id}:workspace-disk",
                provider_id=self.provider_id,
                account_id=account_id,
                region="local",
                storage_type="file_storage",
                persistent=True,
                model_weights_suitable=False,
            )
        ]

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return [
            service(
                service_id=f"{account_id}:c5-http",
                service_name="local-http-inference",
                category="INFERENCE_ENDPOINT",
                provider_id=self.provider_id,
                account_id=account_id,
                enabled=True,
                available=True,
                private_endpoint=True,
                raios_value="PERSISTENT_CONTROL_NODE",
            )
        ]

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return [
            price(
                price_id=f"{account_id}:local-idle",
                kind="ACCOUNT_SPECIFIC_PRICE",
                provider_id=self.provider_id,
                account_id=account_id,
                resource_type="control",
                amount=0,
                pricing_unit="HOUR",
                source="LOCAL_OWNED_SUNK_COST",
                observed_at=utc(),
            )
        ]


class GenericObjectStorageAdapter(ReadOnlyAdapter):
    provider_id = "GENERIC_OBJECT_STORAGE"

    def identify(self) -> dict[str, Any]:
        return provider(
            provider_id=self.provider_id,
            provider_type="generic",
            display_name="Generic object storage",
            supports_compute=False,
            supports_storage=True,
        )

    def discover_accounts(self) -> list[dict[str, Any]]:
        return []

    def discover_regions(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_compute(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_storage(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_services(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_credits(self, account_id: str) -> list[dict[str, Any]]:
        return []

    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]:
        return []


ADAPTERS: dict[str, ReadOnlyAdapter] = {
    "ORACLE_CLOUD": OracleAdapter(),
    "KAGGLE": KaggleAdapter(),
    "LIGHTNING": LightningAdapter(),
    "COLAB": ColabAdapter(),
    "MODAL": ModalAdapter(),
    "GENERIC_SSH": GenericSshAdapter(),
    "GENERIC_HTTP_INFERENCE": GenericHttpInferenceAdapter(),
    "GENERIC_OBJECT_STORAGE": GenericObjectStorageAdapter(),
}
