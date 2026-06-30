import { getCommandCenterMockSnapshot } from "@/services/command-center-api";
import { getAdvisorMockSnapshot } from "@/features/advisor/services/advisor-data";
import { getAdvertisingMockSnapshot } from "@/features/advertising/services/advertising-data";
import { getAutomationMockSnapshot } from "@/features/automation/services/automation-data";
import { getBusinessMockSnapshot } from "@/features/business/services/business-data";
import { getFinanceMockSnapshot } from "@/features/finance/services/finance-data";
import { getInventoryMockSnapshot } from "@/features/inventory/services/inventory-data";
import { getNotificationsMockSnapshot } from "@/features/notifications/services/notifications-data";
import { getProductDetailsMockSnapshot } from "@/features/product-details/services/product-details-data";
import { getProductsMockSnapshot } from "@/features/products/services/products-data";
import { getReportsMockSnapshot } from "@/features/reports/services/reports-data";
import type { WorkspaceDiagnostics } from "@/shared/api";

function createDemoDiagnostics(): WorkspaceDiagnostics {
  return {
    source: "demo",
    degraded: false,
    cached: false,
    stale: false,
    validationStatus: "ok"
  };
}

export function getDemoCommandCenterSnapshot() {
  return {
    ...getCommandCenterMockSnapshot(),
    source: "demo" as const,
    fallbackReason: undefined
  };
}

export function getDemoBusinessSnapshot() {
  return {
    ...getBusinessMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoFinanceSnapshot() {
  return {
    ...getFinanceMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoAdvertisingSnapshot() {
  return {
    ...getAdvertisingMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoProductsSnapshot() {
  return {
    ...getProductsMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoInventorySnapshot() {
  return {
    ...getInventoryMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoAdvisorSnapshot() {
  return {
    ...getAdvisorMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoAutomationSnapshot() {
  return {
    ...getAutomationMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoNotificationsSnapshot() {
  return {
    ...getNotificationsMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoReportsSnapshot() {
  return {
    ...getReportsMockSnapshot(),
    diagnostics: createDemoDiagnostics()
  };
}

export function getDemoProductDetailsSnapshot(sku: string) {
  return {
    ...getProductDetailsMockSnapshot(sku),
    diagnostics: createDemoDiagnostics()
  };
}
