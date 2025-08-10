import {
  SmartContract,
  state,
  State,
  method,
  DeployArgs,
  Permissions,
  Field,
  Signature,
  PublicKey,
  Poseidon,
  Bool,
  Struct,
  UInt64,
  Circuit,
} from 'o1js';

export class PerformanceMetrics extends Struct({
  returns: Field,
  sharpeRatio: Field,
  maxDrawdown: Field,
  volatility: Field,
  timestamp: UInt64,
}) {}

export class PerformanceAuditZkApp extends SmartContract {
  @state(Field) auditCount = State<Field>();
  @state(Field) totalPerformanceScore = State<Field>();
  @state(Bool) auditingActive = State<Bool>();
  @state(Field) lastAuditTimestamp = State<Field>();

  deploy(args: DeployArgs) {
    super.deploy(args);
    this.setPermissions({
      ...Permissions.default(),
      editState: Permissions.proofOrSignature(),
    });
  }

  @method init() {
    super.init();
    this.auditCount.set(Field(0));
    this.totalPerformanceScore.set(Field(0));
    this.auditingActive.set(Bool(true));
    this.lastAuditTimestamp.set(Field(0));
  }

  @method submitPerformanceAudit(
    metrics: PerformanceMetrics,
    auditSignature: Signature,
    auditorPublicKey: PublicKey
  ): Bool {
    const isActive = this.auditingActive.get();
    this.auditingActive.requireEquals(isActive);
    isActive.assertTrue();

    const metricsHash = Poseidon.hash([
      metrics.returns,
      metrics.sharpeRatio,
      metrics.maxDrawdown,
      metrics.volatility,
      metrics.timestamp.toField(),
    ]);

    auditSignature.verify(auditorPublicKey, [metricsHash]);

    const performanceScore = this.calculatePerformanceScore(metrics);
    
    const currentCount = this.auditCount.get();
    this.auditCount.requireEquals(currentCount);
    this.auditCount.set(currentCount.add(1));

    const currentTotal = this.totalPerformanceScore.get();
    this.totalPerformanceScore.requireEquals(currentTotal);
    this.totalPerformanceScore.set(currentTotal.add(performanceScore));

    this.lastAuditTimestamp.set(metrics.timestamp.toField());

    const isValidPerformance = performanceScore.greaterThan(Field(70));
    return isValidPerformance;
  }

  @method calculatePerformanceScore(metrics: PerformanceMetrics): Field {
    const returnsScore = metrics.returns.mul(Field(30));
    const sharpeScore = metrics.sharpeRatio.mul(Field(25));
    const drawdownPenalty = metrics.maxDrawdown.mul(Field(20));
    const volatilityPenalty = metrics.volatility.mul(Field(15));
    
    const baseScore = Field(100);
    const totalScore = baseScore
      .add(returnsScore)
      .add(sharpeScore)
      .sub(drawdownPenalty)
      .sub(volatilityPenalty);

    return totalScore;
  }

  @method getAveragePerformanceScore(): Field {
    const currentCount = this.auditCount.get();
    this.auditCount.requireEquals(currentCount);
    
    const currentTotal = this.totalPerformanceScore.get();
    this.totalPerformanceScore.requireEquals(currentTotal);

    const hasAudits = currentCount.greaterThan(Field(0));
    const averageScore = Circuit.if(
      hasAudits,
      currentTotal.div(currentCount),
      Field(0)
    );

    return averageScore;
  }

  @method pauseAuditing(
    adminSignature: Signature,
    adminPublicKey: PublicKey
  ) {
    const pauseMessage = Poseidon.hash([Field(1)]);
    adminSignature.verify(adminPublicKey, [pauseMessage]);
    
    this.auditingActive.set(Bool(false));
  }

  @method resumeAuditing(
    adminSignature: Signature,
    adminPublicKey: PublicKey
  ) {
    const resumeMessage = Poseidon.hash([Field(2)]);
    adminSignature.verify(adminPublicKey, [resumeMessage]);
    
    this.auditingActive.set(Bool(true));
  }
}
