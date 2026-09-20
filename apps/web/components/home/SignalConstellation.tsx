export function SignalConstellation() {
  return (
    <div className="signal-constellation" aria-hidden="true">
      <div className="signal-constellation__halo signal-constellation__halo--one" />
      <div className="signal-constellation__halo signal-constellation__halo--two" />
      <div className="signal-constellation__orbit signal-constellation__orbit--one" />
      <div className="signal-constellation__orbit signal-constellation__orbit--two" />
      <div className="signal-constellation__line signal-constellation__line--one" />
      <div className="signal-constellation__line signal-constellation__line--two" />
      <div className="signal-constellation__line signal-constellation__line--three" />
      <div className="signal-node signal-node--candidate">
        <span className="signal-node__pulse" />
        <span>Candidate</span>
      </div>
      <div className="signal-node signal-node--evidence">
        <span className="signal-node__pulse" />
        <span>Evidence</span>
      </div>
      <div className="signal-node signal-node--capability">
        <span className="signal-node__pulse" />
        <span>Capability</span>
      </div>
      <div className="signal-node signal-node--interview">
        <span className="signal-node__pulse" />
        <span>Interview</span>
      </div>
      <div className="signal-constellation__core">
        <span className="signal-constellation__core-ring" />
        <span className="signal-constellation__core-mark">CX</span>
      </div>
    </div>
  );
}
