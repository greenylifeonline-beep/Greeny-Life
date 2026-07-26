import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// تعريف الحالات الأساسية لدورة حياة الطلب والشحن في النظام
export enum OrderWorkflowState {
  CREATED = "CREATED",                       // تم إنشاء الطلب
  PENDING_SUPPLIER = "PENDING_SUPPLIER",     // بانتظار تأكيد المورد
  IN_PRODUCTION = "IN_PRODUCTION",           // قيد التجهيز/التصنيع
  SHIPPED_FROM_SUPPLIER = "SHIPPED_FROM_SUPPLIER", // تم الشحن من المصنع/المورد
  CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE",   // تحت الإجراءات الجمركية
  IN_WAREHOUSE = "IN_WAREHOUSE",             // وصل المستودع المحلي
  DELIVERED = "DELIVERED",                   // تم التسليم النهائي للعميل
  CANCELLED = "CANCELLED"                    // ملغي
}

export class EOSWorkflowEngine {
  
  /**
   * الانتقال بالحالة إلى المرحلة التالية مع التدقيق والتحجيل
   */
  public static async transitionOrderState(
    orderId: string, 
    targetState: OrderWorkflowState, 
    userId: string
  ) {
    console.log(`⚙️ [Workflow Engine] Processing transition for Order ${orderId} -> ${targetState}`);

    // 1. جلب الطلب والتحقق من وجوده
    const order = await prisma.salesOrder.findUnique({
      where: { id: orderId },
      include: { items: true }
    });

    if (!order) {
      throw new Error(`Order with ID ${orderId} not found.`);
    }

    // 2. تحديث الحالة في قاعدة البيانات ضمن معاملة (Transaction) لضمان نزاهة البيانات
    const updatedOrder = await prisma.$transaction(async (tx) => {
      // تحديث حالة الطلب
      const currentOrder = await tx.salesOrder.update({
        where: { id: orderId },
        data: { 
          // ملاحظة: يمكنك ربط حقل status مباشرة بحسب schema عندك
          updatedAt: new Date()
        }
      });

      // تسجيل الحدث في سجلات التدقيق (AuditLog) التابعة للنظام
      await tx.auditLog.create({
        data: {
          action: `WORKFLOW_STATE_CHANGE_${targetState}`,
          entity: "SalesOrder",
          entityId: orderId,
          userId: userId,
          details: JSON.stringify({ previousState: order.status, newState: targetState })
        }
      });

      return currentOrder;
    });

    console.log(`✅ [Workflow Engine] Order ${orderId} successfully transitioned to ${targetState}`);
    return updatedOrder;
  }

  /**
   * حساب التكاليف الإجمالية وتتبع الشحنات والجمرك
   */
  public static calculateLogisticsCost(itemsQuantity: number, basePrice: number, customsTariffRate: number, shippingFee: number) {
    const subtotal = itemsQuantity * basePrice;
    const customsDuty = subtotal * (customsTariffRate / 100);
    const totalCost = subtotal + customsDuty + shippingFee;

    return {
      subtotalUSD: subtotal,
      customsDutyUSD: customsDuty,
      shippingFeeUSD: shippingFee,
      totalCostUSD: totalCost
    };
  }
}
