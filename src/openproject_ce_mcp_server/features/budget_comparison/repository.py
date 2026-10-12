"""PostgreSQL adapter for the OpenProject 17.9 budget comparison read model."""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class BudgetComparisonRepository:
    """Read-only repository; only parameterized, fixed SELECT statements are used."""

    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self._pool = pool

    async def compare(self, project_ids: list[int], user_id: int, include_subprojects: bool) -> list[dict[str, Any]]:
        query = """
        WITH RECURSIVE tree AS (
          SELECT p.id, p.name, p.identifier, p.parent_id, 0 AS depth
          FROM projects p WHERE p.id = ANY(%s::int[])
          UNION ALL
          SELECT child.id, child.name, child.identifier, child.parent_id, tree.depth + 1
          FROM projects child JOIN tree ON child.parent_id = tree.id
          WHERE %s AND tree.depth < 32
        ), principals AS (
          SELECT %s::int AS id
          UNION
          SELECT gu.group_id FROM group_users gu WHERE gu.user_id = %s
        ), project_permissions AS (
          SELECT t.id AS project_id,
                 bool_or(rp.permission = 'view_project') AS can_view_project,
                 bool_or(rp.permission = 'view_budgets') AS can_view_budgets,
                 bool_or(rp.permission = 'view_cost_rates') AS can_view_costs,
                 bool_or(rp.permission = 'view_hourly_rates') AS can_view_hourly_rates,
                 COALESCE(bool_or(u.admin), false) AS is_admin
          FROM tree t
          LEFT JOIN members m ON m.project_id = t.id
          LEFT JOIN principals pr ON (m.user_id = pr.id OR (m.entity_type = 'Principal' AND m.entity_id = pr.id))
          LEFT JOIN member_roles mr ON mr.member_id = m.id
          LEFT JOIN role_permissions rp ON rp.role_id = mr.role_id
          LEFT JOIN users u ON u.id = %s
          GROUP BY t.id
        ), visible_tree AS (
          SELECT t.* FROM tree t
          JOIN project_permissions pp ON pp.project_id = t.id
          WHERE pp.is_admin OR (
            pp.can_view_project AND pp.can_view_budgets AND pp.can_view_costs AND pp.can_view_hourly_rates
          )
        ), per_project AS (
          SELECT vt.id, vt.name, vt.identifier, vt.parent_id, vt.depth,
                 COALESCE((
                   SELECT sum(
                     COALESCE(b.base_amount, 0)
                     + COALESCE((SELECT sum(COALESCE(mbi.amount,
                         mbi.units * COALESCE((SELECT cr.rate FROM rates cr
                           WHERE cr.type = 'CostRate' AND cr.cost_type_id = mbi.cost_type_id
                             AND cr.valid_from <= b.fixed_date
                           ORDER BY cr.valid_from DESC LIMIT 1), 0)))
                       FROM material_budget_items mbi WHERE mbi.budget_id = b.id), 0)
                     + COALESCE((SELECT sum(COALESCE(lbi.amount,
                         lbi.hours * COALESCE(
                           (SELECT hr.rate FROM rates hr
                             JOIN projects rate_project ON rate_project.id = hr.project_id
                             JOIN projects budget_project ON budget_project.id = b.project_id
                             WHERE hr.type = 'HourlyRate' AND hr.user_id = lbi.user_id
                               AND hr.valid_from <= b.fixed_date
                               AND rate_project.lft <= budget_project.lft AND rate_project.rgt >= budget_project.rgt
                             ORDER BY rate_project.lft DESC, hr.valid_from DESC LIMIT 1),
                           (SELECT dhr.rate FROM rates dhr
                             WHERE dhr.type = 'DefaultHourlyRate' AND dhr.user_id = lbi.user_id
                               AND dhr.valid_from <= b.fixed_date
                             ORDER BY dhr.valid_from DESC LIMIT 1), 0)))
                       FROM labor_budget_items lbi WHERE lbi.budget_id = b.id), 0)
                   ) FROM budgets b WHERE b.project_id = vt.id
                 ), 0)::numeric AS planned,
                 (COALESCE((SELECT sum(COALESCE(c.overridden_costs, c.costs, 0))
                   FROM cost_entries c JOIN work_packages wp
                     ON wp.id = c.entity_id AND c.entity_type = 'WorkPackage'
                   WHERE wp.project_id = vt.id AND wp.budget_id IS NOT NULL), 0)
                  + COALESCE((SELECT sum(COALESCE(te.overridden_costs, te.costs, 0))
                   FROM time_entries te JOIN work_packages wp
                     ON wp.id = te.entity_id AND te.entity_type = 'WorkPackage'
                   WHERE wp.project_id = vt.id AND wp.budget_id IS NOT NULL), 0))::numeric AS spent
          FROM visible_tree vt
        )
        SELECT id, name, identifier, parent_id, depth, planned, spent
        FROM per_project ORDER BY depth, id
        """
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute("SET TRANSACTION READ ONLY")
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (project_ids, include_subprojects, user_id, user_id, user_id))
                return list(await cursor.fetchall())
