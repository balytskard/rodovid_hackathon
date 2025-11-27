import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import './TreeView.css';
import { CryptoModule } from '../utils/crypto';

function TreeView({ data, isEncrypted, onNodeClick, selectedNode }) {
  const svgRef = useRef();
  const containerRef = useRef();
  const [decryptedData, setDecryptedData] = useState(null);

  // --- 1. Розшифрування даних ---
  useEffect(() => {
    const decryptNodes = async () => {
      if (!data || !data.nodes) return;
      if (isEncrypted) {
        setDecryptedData(data);
        return;
      }

      const decryptedNodes = await Promise.all(
        data.nodes.map(async (node) => {
          const decryptedNode = { ...node };
          if (node.name_blob?.startsWith('ENC_')) {
            try { decryptedNode.name = await CryptoModule.decrypt(node.name_blob); } 
            catch { decryptedNode.name = '[Error]'; }
          } else {
            decryptedNode.name = node.name || node.name_blob || `ID:${node.id.substring(0,4)}`;
          }
          if (node.birth_date_blob?.startsWith('ENC_')) {
            try { decryptedNode.birth = await CryptoModule.decrypt(node.birth_date_blob); }
            catch { decryptedNode.birth = ''; }
          } else {
            decryptedNode.birth = node.birth || node.birth_date_blob;
          }
          return decryptedNode;
        })
      );
      setDecryptedData({ ...data, nodes: decryptedNodes });
    };
    decryptNodes();
  }, [data, isEncrypted]);

  // --- ХЕЛПЕР: Знайти найстарішого предка для конкретної людини ---
  const findRootAncestor = (startNodeId, nodes, links) => {
    let currentId = startNodeId;
    let hasParent = true;

    // Піднімаємось вгору, поки є батьки
    while (hasParent) {
        // Шукаємо зв'язок, де currentId є target (дитиною)
        const parentLink = links.find(l => l.target === currentId && l.type === 'PARENT_OF');
        if (parentLink) {
            currentId = parentLink.source;
        } else {
            hasParent = false;
        }
    }
    
    // Перевіряємо, чи цей предок не є дружиною когось іншого (щоб не почати дерево з жінки, якщо є чоловік)
    const spouseLink = links.find(l => l.target === currentId && l.type === 'SPOUSE');
    if (spouseLink) {
        // Якщо це дружина, беремо чоловіка як корінь (для краси візуалізації)
        // (Це спрощення, але для d3.tree краще мати чоловіка зліва/зверху)
        return spouseLink.source; 
    }

    return currentId;
  };

  // --- 2. Логіка трансформації: Люди -> Сім'ї ---
  const buildFamilyTree = (nodes, links, targetRootId = null) => {
    const nodeMap = new Map(nodes.map(n => [n.id, { ...n }]));
    
    const getYear = (dateStr) => {
        if (!dateStr) return 9999;
        const match = dateStr.toString().match(/\d{4}/);
        return match ? parseInt(match[0]) : 9999;
    };

    let rootPersonId = targetRootId;

    // Якщо конкретний корінь не заданий, шукаємо глобально найстарішого
    if (!rootPersonId) {
        const childIds = new Set(links.filter(l => l.type === 'PARENT_OF').map(l => l.target));
        let rootCandidates = nodes.filter(n => !childIds.has(n.id));
        rootCandidates.sort((a, b) => getYear(a.birth) - getYear(b.birth));
        if (rootCandidates.length > 0) {
            rootPersonId = rootCandidates[0].id;
        }
    }

    if (!rootPersonId) return null;

    // Рекурсивна функція: повертає Вузол "Сім'я"
    const buildFamilyNode = (primaryPersonId) => {
        const person = nodeMap.get(primaryPersonId);
        if (!person) return null;

        // 1. Шукаємо подружжя
        const spouseLink = links.find(l => 
            (l.source === primaryPersonId || l.target === primaryPersonId) && l.type === 'SPOUSE'
        );
        
        let spouse = null;
        if (spouseLink) {
            const spouseId = spouseLink.source === primaryPersonId ? spouseLink.target : spouseLink.source;
            spouse = nodeMap.get(spouseId);
        }

        // 2. Шукаємо дітей
        const childrenIds = new Set();
        links.filter(l => l.type === 'PARENT_OF' && l.source === primaryPersonId).forEach(l => childrenIds.add(l.target));
        if (spouse) {
            links.filter(l => l.type === 'PARENT_OF' && l.source === spouse.id).forEach(l => childrenIds.add(l.target));
        }

        // 3. Формуємо дітей-сімей рекурсивно
        const childrenNodes = Array.from(childrenIds)
            .map(childId => buildFamilyNode(childId)) 
            .filter(n => n)
            .sort((a, b) => getYear(a.primary.birth) - getYear(b.primary.birth));

        return {
            primary: person, 
            spouse: spouse, 
            children: childrenNodes,
            isFamily: true,
            id: person.id // ID сім'ї прив'язуємо до primary
        };
    };

    return buildFamilyNode(rootPersonId);
  };

  // --- 3. Рендеринг ---
  useEffect(() => {
    if (!decryptedData || !containerRef.current) return;

    // А. Визначаємо корінь дерева
    let activeRootId = null;
    
    if (selectedNode) {
        // Якщо вибрано вузол, знаходимо його найвищого предка і будуємо дерево від нього
        activeRootId = findRootAncestor(selectedNode.id, decryptedData.nodes, decryptedData.links);
    }

    // Б. Будуємо дані для D3
    const rootData = buildFamilyTree(decryptedData.nodes, decryptedData.links, activeRootId);
    if (!rootData) return;

    const width = containerRef.current.clientWidth || 800;
    const height = 600;
    const nodeWidth = 220; 
    const nodeHeight = 160;

    // В. Ініціалізація SVG
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
        .attr('width', width)
        .attr('height', height);

    const zoomGroup = svg.append("g");
    
    const zoom = d3.zoom()
        .scaleExtent([0.1, 2])
        .on("zoom", (e) => zoomGroup.attr("transform", e.transform));
    
    svg.call(zoom);

    // Подвійний клік для скидання зуму
    svg.on("dblclick.zoom", () => {
        svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    });

    const g = zoomGroup.append("g").attr("transform", "translate(40, 40)");

    const root = d3.hierarchy(rootData);
    const treeMap = d3.tree().nodeSize([nodeWidth, nodeHeight]);
    const nodes = treeMap(root);

    // Г. Центрування дерева при старті (щоб не було за краєм)
    let minX = Infinity;
    root.each(d => { if (d.x < minX) minX = d.x; });
    const initialTranslateX = -minX + width/2;
    g.attr("transform", `translate(${initialTranslateX}, 50)`);

    // --- Д. Авто-центрування на вибраному вузлі ---
    if (selectedNode) {
        // Знаходимо координати сім'ї, де є selectedNode
        const targetFamilyNode = nodes.descendants().find(d => 
            d.data.primary.id === selectedNode.id || 
            (d.data.spouse && d.data.spouse.id === selectedNode.id)
        );

        if (targetFamilyNode) {
            const scale = 1;
            const x = -targetFamilyNode.x * scale + width / 2;
            const y = -targetFamilyNode.y * scale + height / 2;
            
            // Плавна анімація камери до вузла
            svg.transition()
               .duration(750)
               .call(zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
        }
    }


    // --- МАЛЮВАННЯ ---
    
    g.selectAll(".link")
        .data(nodes.links())
        .enter()
        .append("path")
        .attr("class", "link")
        .attr("fill", "none")
        .attr("stroke", "#ccc")
        .attr("stroke-width", 2)
        .attr("d", d => d3.linkVertical().x(node => node.x).y(node => node.y)(d));

    const nodeGroup = g.selectAll(".node")
        .data(nodes.descendants())
        .enter()
        .append("g")
        .attr("class", "node")
        .attr("transform", d => `translate(${d.x},${d.y})`);

    // Функція малювання кружечка
    const renderPerson = (selection, personData, offsetX) => {
        if (!personData) return;
        
        const group = selection.append("g")
            .attr("transform", `translate(${offsetX}, 0)`)
            .style("cursor", "pointer")
            .on("click", (e) => {
                e.stopPropagation();
                onNodeClick(personData);
            });

        group.append("circle")
            .attr("r", 30)
            .attr("fill", d => {
                if (selectedNode?.id === personData.id) return "#FF9800";
                return "#81C784";
            })
            .attr("stroke", "#fff")
            .attr("stroke-width", selectedNode?.id === personData.id ? 3 : 2);

        group.append("text")
            .attr("dy", 5)
            .attr("text-anchor", "middle")
            .style("fill", "white")
            .style("font-weight", "bold")
            .text(personData.name ? personData.name.substring(0, 2).toUpperCase() : "?");
            
        group.append("text")
            .attr("dy", 45)
            .attr("text-anchor", "middle")
            .style("font-size", "12px")
            .text(personData.name ? (personData.name.length > 10 ? personData.name.slice(0,10)+'...' : personData.name) : "Unknown");
            
        group.append("text")
            .attr("dy", 60)
            .attr("text-anchor", "middle")
            .style("font-size", "10px")
            .style("fill", "#666")
            .text(personData.birth || "");
            
        return group;
    };

    nodeGroup.each(function(d) {
        const group = d3.select(this);
        const family = d.data;

        if (family.spouse) {
            group.append("line")
                .attr("x1", -40).attr("y1", 0)
                .attr("x2", 40).attr("y2", 0)
                .attr("stroke", "#E91E63").attr("stroke-width", 2).attr("stroke-dasharray", "4");
                
            renderPerson(group, family.primary, -40);
            const spouseG = renderPerson(group, family.spouse, 40);
            if(spouseG) spouseG.select("circle").attr("fill", selectedNode?.id === family.spouse.id ? "#FF9800" : "#F06292");
            
        } else {
            renderPerson(group, family.primary, 0);
        }
    });

  }, [decryptedData, selectedNode, onNodeClick]);

  return (
    <div className="tree-container card" ref={containerRef} style={{ height: '600px', overflow: 'hidden' }}>
      <svg ref={svgRef}></svg>
    </div>
  );
}

export default TreeView;