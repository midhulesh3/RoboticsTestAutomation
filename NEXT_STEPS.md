# HRTF Next Steps

The MVP has been initialized and core execution logic has been implemented.

**Completed in this session:**
1. Built the `ExecutionOrchestrator` integrating all core layers (loader, adapter, logger, assertions).
2. Connected `ExecutionOrchestrator` to the `hrtf run` CLI command to run test and generate `RunResult`.
3. Created an integration test for a full run with the `MuJoCoAdapter`.
4. Implemented `ReachesWithin` and `StabilisesWithin` assertions.
5. Implemented `hrtf init` command to bootstrap scenarios.

**Remaining Tasks for MVP / Next Session:**

1. **Baseline Manager (`hrtf/baselines/`)**
   - Implement logic to capture a successful `RunResult` and store it as a baseline (JSON).
   - Implement baseline comparison (computing % delta for signal summaries and failing on tolerance violations).
   - Connect to `hrtf baseline capture` and `hrtf baseline compare` CLI commands.
2. **Reporting Generation (`hrtf/reporting/`)**
   - Implement `ReportGenerator` to convert `RunResult` JSON into HTML plots (using `matplotlib`).
   - Connect to the `hrtf report` CLI command.
3. **Compound Assertions (`hrtf/assertions/compound.py`)**
   - Implement the `CompoundAssertion` class (AND/OR logic for multiple predicates).
4. **Enhanced YAML validation**
   - Expand `hrtf/scenario/parser.py` to utilize `jsonschema` with the published `scenario_v1.json` schema.