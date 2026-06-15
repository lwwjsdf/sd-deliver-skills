# business_logic.yaml 模板片段

这个文件提供可复用的 YAML 配置片段，客户可以复制到自己的 `rules/business_logic.yaml` 中。

## 1. Product_Order_Payment 派生 Product_Payment_Detail

```yaml
event_sequences:
  - name: purchase
    condition: "segment in [L2, L3, L4]"
    conversion_rate: 0.6
    events:
      - event: Product_Order_Payment
        fields:
          productName: "Special Exhibition"
          businessUnit: "M+"
          productType: "展览"
          ticketsQuantity: 2
          orderPaidAmount: 500.00
          paymentMethod: "微信支付"
          isSuccess: true
          ifAdditionalPurchase: false
        derive:
          event: Product_Payment_Detail
          count_ref: "{Product_Order_Payment.ticketsQuantity}"
          distribute_fields:
            ticketPaidAmount:
              source: orderPaidAmount
              strategy: divide_evenly
          prefix_fields:
            ticketID: "TICKET-{timestamp}-{detailIndex:03d}"
          carry_fields:
            - productName
            - businessUnit
            - productType
            - paymentMethod
            - isSuccess
          gap_seconds: 1
```

说明：
- `count_ref`: 从父事件字段读取派生事件数量（这里用 ticketsQuantity）
- `distribute_fields`: 把父事件字段均分到每个子事件；支持 `source` 指定父事件字段名，目标字段名可不同
- `prefix_fields`: 为每个子事件生成不同 ID，支持 `{timestamp}`、`{random}`、`{orderIndex}`、`{detailIndex}` 变量
- `carry_fields`: 子事件继承父事件的字段
- `gap_seconds`: 子事件与父事件的时间间隔

旧写法（仍兼容）：

```yaml
          distribute_fields:
            paidAmount: divide_evenly   # 父事件字段与子事件字段同名
```

## 2. 会员过期时间分布

```yaml
property_enums:
  mPlusMembershipExpirationTime:
    type: date_relative_to_today
    distribution:
      expired: 0.3
      active: 0.7
    expired_range: [-365, -1]
    active_range: [1, 365]

  palaceMembershipExpirationTime:
    type: date_relative_to_today
    distribution:
      expired: 0.3
      active: 0.7
    expired_range: [-365, -1]
    active_range: [1, 365]
```

## 3. 票数量分布

```yaml
property_enums:
  ticketsQuantity:
    type: weighted_int
    values:
      - {value: 1, weight: 0.3}
      - {value: 2, weight: 0.4}
      - {value: 3, weight: 0.2}
      - {value: 4, weight: 0.1}
```

## 4. 订单金额范围

```yaml
property_enums:
  paidAmount:
    type: range
    min: 100
    max: 2000
```
