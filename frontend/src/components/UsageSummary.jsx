function formatCost(cost) {
  if (!cost) return "$0.00";
  return cost < 0.01 ? `$${cost.toFixed(6)}` : `$${cost.toFixed(4)}`;
}

function agentLabel(agent) {
  if (agent === "analyzer") return "Analyzer";
  if (agent === "remediation") return "Remediation";
  return agent;
}

export default function UsageSummary({ usage }) {
  const calls = usage?.calls || [];

  if (calls.length === 0) {
    return (
      <div className="p-8 text-center border bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <p className="font-mono text-xs text-slate-400">
          No LLM calls for this scan -- nothing to analyze meant nothing to spend.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
          <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
            Total Tokens
          </dt>
          <dd className="font-mono text-base font-semibold text-slate-100">
            {usage.total_tokens.toLocaleString()}
          </dd>
        </div>
        <div className="p-3 border rounded-lg bg-slate-950/50 border-slate-800/60">
          <dt className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
            Total Cost
          </dt>
          <dd className="font-mono text-base font-semibold text-cyan-300">
            {formatCost(usage.total_cost_usd)}
          </dd>
        </div>
      </div>

      <div className="overflow-hidden border shadow-xl bg-slate-900/60 backdrop-blur-xl border-slate-800/80 rounded-xl ring-1 ring-white/5">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="border-b bg-slate-950/80 border-slate-800/80">
              <tr>
                <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                  Agent
                </th>
                <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                  Model
                </th>
                <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                  Prompt
                </th>
                <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                  Completion
                </th>
                <th className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold px-4 py-3">
                  Cost
                </th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs divide-y divide-slate-800/60">
              {calls.map((c, i) => (
                <tr key={i} className="align-top transition-colors hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-slate-200 whitespace-nowrap">{agentLabel(c.agent)}</td>
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{c.model}</td>
                  <td className="px-4 py-3 text-slate-300">{c.prompt_tokens.toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-300">{c.completion_tokens.toLocaleString()}</td>
                  <td className="px-4 py-3 text-cyan-300">{formatCost(c.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
