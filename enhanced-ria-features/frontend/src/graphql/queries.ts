import { gql } from '@apollo/client';

export const GET_VOTING_HEATMAP_DATA = gql`
  query GetVotingHeatmapData {
    votingHeatmapData {
      vote_id
      timestamp
      vote_intensity
      zkp_status
      source_reliability
      stake_weight
      x_coord
      y_coord
    }
  }
`;

export const GET_CAUSAL_GRAPH_DATA = gql`
  query GetCausalGraphData {
    causalGraphData {
      nodes {
        id
        label
        x
        y
        strength
        node_type
      }
      edges {
        source
        target
        strength
        granger_p_value
        confidence
      }
    }
  }
`;

export const GET_SYSTEM_STATUS = gql`
  query GetSystemStatus {
    systemStatus {
      metrics {
        total_votes_processed
        successful_votes
        failed_votes
        avg_processing_time_ms
        total_anomalies_detected
        causal_relationships_discovered
        model_accuracy
      }
      feature_status {
        source_reliability
        ipfs_storage
        heatmap_ui
        delay_alerts
        zkp_proofs
        causal_ai
      }
    }
  }
`;

export const GET_COMPLIANCE_STATUS = gql`
  query GetComplianceStatus {
    complianceStatus {
      metrics {
        sec_compliance_score
        audit_trail_integrity
        zkp_verification_rate
        data_retention_compliance
        last_audit_date
        next_audit_due
      }
      alerts {
        id
        type
        message
        timestamp
        resolved
      }
    }
  }
`;
