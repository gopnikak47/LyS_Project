"""Ma trận phân quyền (FR-03).

| Quyền              | ADMIN | ANALYST | VIEWER |
|--------------------|:-----:|:-------:|:------:|
| report:view        |   ✓   |    ✓    |   ✓    |
| survey:edit        |   ✓   |    ✓    |        |
| label:edit         |   ✓   |    ✓    |        |
| data:export        |   ✓   |    ✓    |        |
| topic:manage       |   ✓   |    ✓    |        |
| member:manage      |   ✓   |         |        |
| workspace:manage   |   ✓   |         |        |
| tenant:manage      |   ✓   |         |        |
| label:approve      |   ✓   |         |        |

Phạm vi workspace: ADMIN luôn thấy mọi workspace; ANALYST/VIEWER thấy tất cả nếu
`memberships.all_workspaces = true`, ngược lại chỉ các workspace trong `workspace_members`.
"""

from __future__ import annotations

from enum import StrEnum

from app.models.enums import Role


class Permission(StrEnum):
    REPORT_VIEW = "report:view"
    SURVEY_EDIT = "survey:edit"
    LABEL_EDIT = "label:edit"
    LABEL_APPROVE = "label:approve"
    DATA_EXPORT = "data:export"
    TOPIC_MANAGE = "topic:manage"
    MEMBER_MANAGE = "member:manage"
    WORKSPACE_MANAGE = "workspace:manage"
    TENANT_MANAGE = "tenant:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.ANALYST: frozenset(
        {
            Permission.REPORT_VIEW,
            Permission.SURVEY_EDIT,
            Permission.LABEL_EDIT,
            Permission.DATA_EXPORT,
            Permission.TOPIC_MANAGE,
        }
    ),
    Role.VIEWER: frozenset({Permission.REPORT_VIEW}),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]
