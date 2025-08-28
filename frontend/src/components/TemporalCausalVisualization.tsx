import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface CausalNode {
  id: string;
  type: string;
  timestamp: string;
  location?: string;
  influenceStrength: number;
}

interface CausalEdge {
  source: string;
  target: string;
  type: string;
  strength: number;
  lagMinutes: number;
  confidence: number;
}

interface TemporalCausalGraphProps {
  nodes: CausalNode[];
  edges: CausalEdge[];
  width?: number;
  height?: number;
  timeRange?: [Date, Date];
}

const TemporalCausalVisualization: React.FC<TemporalCausalGraphProps> = ({
  nodes,
  edges,
  width = 800,
  height = 600,
  timeRange,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredNode, setHoveredNode] = useState<CausalNode | null>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${width / 2}, ${height / 2})`);

    const effectiveTimeRange = timeRange || [
      new Date(Math.min(...nodes.map(n => new Date(n.timestamp).getTime()))),
      new Date(Math.max(...nodes.map(n => new Date(n.timestamp).getTime())))
    ];

    const timeScale = d3.scaleTime()
      .domain(effectiveTimeRange)
      .range([-width / 2 + 100, width / 2 - 100]);

    const nodeMap = new Map(nodes.map(node => [node.id, node]));

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(edges as any)
        .id((d: any) => d.id)
        .distance(d => 100 / (d as any).strength))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('x', d3.forceX((d: any) => {
        const nodeTime = new Date(d.timestamp);
        return timeScale(nodeTime);
      }).strength(0.5))
      .force('y', d3.forceY(0).strength(0.1))
      .force('collision', d3.forceCollide().radius(30));

    const timeAxis = d3.axisBottom(timeScale)
      .ticks(5)
      .tickFormat(d3.timeFormat('%b %d, %H:%M'));

    svg.append('g')
      .attr('transform', `translate(0, ${height / 2 - 50})`)
      .call(timeAxis)
      .selectAll('text')
      .attr('transform', 'rotate(-45)')
      .style('text-anchor', 'end');

    const link = svg.append('g')
      .selectAll('line')
      .data(edges)
      .enter()
      .append('line')
      .attr('stroke-width', d => Math.max(1, d.strength * 5))
      .attr('stroke', d => {
        const confidence = d.confidence || 0.5;
        return d3.interpolateRdYlGn(confidence);
      })
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrow)');

    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .enter()
      .append('circle')
      .attr('r', d => 5 + d.influenceStrength * 15)
      .attr('fill', d => {
        switch (d.type) {
          case 'market_event': return '#4285F4';
          case 'causal_driver': return '#EA4335';
          case 'price_movement': return '#34A853';
          case 'epidemic_event': return '#FBBC05';
          case 'epidemic_timepoint': return '#FF6D01';
          default: return '#999999';
        }
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .on('mouseover', (event, d) => {
        setHoveredNode(d);
      })
      .on('mouseout', () => {
        setHoveredNode(null);
      })
      .call(d3.drag()
        .on('start', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d: any) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }) as any);

    const label = svg.append('g')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .text(d => d.id.split('_').slice(-1)[0])
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4)
      .style('pointer-events', 'none');

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      label
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    const legend = svg.append('g')
      .attr('transform', `translate(${-width / 2 + 20}, ${-height / 2 + 20})`);

    const legendItems = [
      { type: 'market_event', color: '#4285F4', label: 'Market Event' },
      { type: 'causal_driver', color: '#EA4335', label: 'Causal Driver' },
      { type: 'price_movement', color: '#34A853', label: 'Price Movement' },
      { type: 'epidemic_event', color: '#FBBC05', label: 'Epidemic Event' },
      { type: 'epidemic_timepoint', color: '#FF6D01', label: 'Epidemic Timepoint' },
    ];

    legendItems.forEach((item, i) => {
      const legendRow = legend.append('g')
        .attr('transform', `translate(0, ${i * 20})`);
      
      legendRow.append('circle')
        .attr('r', 6)
        .attr('fill', item.color);
      
      legendRow.append('text')
        .attr('x', 15)
        .attr('y', 4)
        .text(item.label)
        .style('font-size', '12px');
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, width, height, timeRange]);

  return (
    <div className="temporal-causal-visualization">
      <svg ref={svgRef} />
      {hoveredNode && (
        <div className="node-tooltip" style={{ position: 'absolute', top: '10px', right: '10px', padding: '10px', background: 'white', border: '1px solid #ccc', borderRadius: '4px' }}>
          <h4>{hoveredNode.id}</h4>
          <p>Type: {hoveredNode.type}</p>
          <p>Time: {new Date(hoveredNode.timestamp).toLocaleString()}</p>
          <p>Influence: {(hoveredNode.influenceStrength * 100).toFixed(1)}%</p>
          {hoveredNode.location && <p>Location: {hoveredNode.location}</p>}
        </div>
      )}
    </div>
  );
};

export default TemporalCausalVisualization;
