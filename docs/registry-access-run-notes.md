# Pod K registry — Team 21 access and run notes

Use this page as the **Access/Run Notes** link in the class endpoint registry.
Neither Team 21's Render deployments nor their interactive API docs require
GitHub repository access. Authentication for an API call is separate from
GitHub access.

## Correct URLs

| Purpose | URL | Browser guidance |
|---|---|---|
| Team 21 system base URL | https://team21-cra-reporting-service.onrender.com | API base URL, **not** a human-facing login page |
| Team 21 system docs | https://team21-cra-reporting-service.onrender.com/docs | Swagger UI (interactive API documentation) |
| Team 21 system health | https://team21-cra-reporting-service.onrender.com/health | Public `GET`; expect HTTP 200 |
| Team 21 automated tester base URL | https://cra-phase3-tester.onrender.com | API base URL, **not** the run endpoint |
| Team 21 tester docs | https://cra-phase3-tester.onrender.com/docs | Swagger UI; use **Try it out** |
| Team 21 tester health | https://cra-phase3-tester.onrender.com/health | Public `GET`; expect `{"status":"ok"}` |

If a browser shows **401 Unauthorized** or **Not authorized** after clicking a
protected system endpoint, this is expected without a bearer token. The system
requires `Authorization: Bearer <token>` for all endpoints except
`GET /health`; ticket-changing calls also require nonblank `X-Actor`.
Do not put any bearer token in the public registry, GitHub source, screenshots
or chat messages. Get the target system's evaluation credential through the
authorized team/course channel.

## Run Team 21's deployed tester in Swagger UI

This protocol calls **POST**, so simply visiting a `/test/run` URL in a browser
will not start a test.

1. Open [Team 21 tester Swagger UI](https://cra-phase3-tester.onrender.com/docs).
2. Expand **POST /test/setup**, click **Try it out**, enter the JSON request
   below, then **Execute**:

   ```json
   {"target_url": "https://team21-cra-reporting-service.onrender.com"}
   ```

   You may substitute another podmate's **system base URL** if it is a configured
   and authorized target. Successful setup returns HTTP 201 and a `session_id`.
   A 401 returned during setup usually indicates the tester was not configured
   with the target's API credential; contact the Team 21 operator.
3. Expand **POST /test/run**, click **Try it out**, enter:

   ```json
   {"session_id": "PASTE_SESSION_ID_FROM_SETUP"}
   ```

   Execute **once** and let the request complete. The tester returns an
   acceptance report containing per-AC outcomes and coverage. This can take
   several minutes, particularly on a small/free tester instance.
4. To retrieve an already finished report, expand **GET /test/report** and
   enter the same `session_id` in its query parameter.

**Important:** A test run resets and populates its target evaluation database.
Coordinate with both teams so no other acceptance or persistence test is
running on the same target. Tester sessions are stored in process memory and
may be lost on a Render restart; create a new session if an earlier ID becomes
unknown. Avoid repeating an interrupted destructive run without coordination.

## Equivalent terminal commands (no GitHub checkout required)

Replace the target only when it is an authorized/configured evaluation system.
Run the setup first, copy the `session_id` from the response, then run:

```bash
TESTER="https://cra-phase3-tester.onrender.com"
TARGET="https://team21-cra-reporting-service.onrender.com"
curl -i -sS -X POST "$TESTER/test/setup" \
  -H 'Content-Type: application/json' \
  --data "{\"target_url\":\"$TARGET\"}"

# Replace the placeholder with the session_id returned above.
SESSION_ID="PASTE_SESSION_ID_FROM_SETUP"
curl -i -sS --max-time 1200 -X POST "$TESTER/test/run" \
  -H 'Content-Type: application/json' \
  --data "{\"session_id\":\"$SESSION_ID\"}"
curl -i -sS "$TESTER/test/report?session_id=$SESSION_ID"
```

This public tester route does **not** require GitHub login or its own bearer
header. It supplies the **target system** bearer token from its protected
Render `TARGET_TOKENS_JSON` configuration. The target is not guaranteed to
be supported unless its credential is configured.

## Existing evidence

- [Deployed self-validation](https://github.com/WConrad44/cra-reporting-service/actions/runs/45068594561):
  18/18 using the Team 21 tester source on a GitHub-hosted runner.
- [Reciprocal cross-team validation](https://github.com/WConrad44/cra-reporting-service/actions/runs/45069249377):
  Team 21 tester against Team 17: 18/18; Team 17 tester against Team 21:
  241/241. This particular run used the **Render-hosted Team 21 tester** for
  the forward direction.
- [Phase 5 operational guide](phase5-operations.md).

The registry should contain **service and tester base URLs** plus a link to
this page under Access/Run Notes. Do not substitute the GitHub repository URL
for either deployed endpoint.
