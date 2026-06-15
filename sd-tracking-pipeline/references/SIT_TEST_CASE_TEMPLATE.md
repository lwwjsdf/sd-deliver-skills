# SIT Test Case 模板

复制到项目 `references/sit-test-case.xlsx`，一个 sheet 即可。

## 列说明

| 列 | 说明 |
|----|------|
| Release Number | 版本号，如 1.0.0 |
| Test Case Description | 用例描述 |
| Test Case ID | 唯一编号，如 TC1.1、TC-CUST-001 |
| Precondition | 前置条件 |
| Step Number and Description | 步骤编号 + 操作说明 |
| Expected Result | 期望结果 |
| Priority | P0 / P1 / P2 |
| Status | Pass / Fail / Block / N/A |
| Tester | 执行人 |
| Test Date | 执行日期 |
| Bug/Remark | 缺陷或备注 |

## 示例数据

| Release Number | Test Case Description | Test Case ID | Precondition | Step Number and Description | Expected Result | Priority | Status |
|----------------|----------------------|--------------|--------------|----------------------------|-----------------|----------|--------|
| 1.0.0 | Verify Product_Order_Payment event can be triggered and captured | TC-CUST-001 | Mini Program SDK integrated, test account ready | 1. Open MP product page 2. Click purchase 3. Complete payment | Event `Product_Order_Payment` appears in CDP within 5s with all required properties | P0 | |
| 1.0.0 | Verify Product_Payment_Detail derived from order | TC-CUST-002 | Product_Order_Payment event exists | 1. Query CDP by orderId 2. Check detail events | Number of `Product_Payment_Detail` events equals `ticketsQuantity`; ticketID unique | P0 | |
| 1.0.0 | Verify public property platformType | TC-PUB-001 | Any event exists | 1. Check event properties | `platformType` = "MP" or "Web" | P0 | |
| 1.0.0 | Verify user attribute registerTime | TC-USER-001 | Registration_Result(isSuccess=true) exists | 1. Query user profile | `registerTime` is populated | P1 | |
