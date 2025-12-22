<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import QuoteLine from '$lib/components/QuoteLine.svelte';
	import LogsIndexingCalculator from '$lib/components/LogsIndexingCalculator.svelte';
	import { fetchProducts, fetchMetadata, createQuote, updateQuote, fetchRegions, fetchAllotments, initAllotments, syncPricing, type Product, type PricingMetadata, type Region, type Allotment } from '$lib/api';
	import { formatCurrency, parsePrice, formatNumber, isPercentagePrice, parsePercentage } from '$lib/utils';

	interface LineItem {
		id: string;
		product: Product | null;
		quantity: number;
		isAllotment?: boolean;
		parentLineId?: string;
		allotmentInfo?: Allotment;
		includedQuantity?: number;
	}

	let products: Product[] = [];
	let metadata: PricingMetadata | null = null;
	let regions: Record<string, Region> = {};
	let allotments: Allotment[] = [];
	let selectedRegion = 'us';
	let selectedPlan: 'Pro' | 'Enterprise' = 'Pro';
	let lines: LineItem[] = [{ id: crypto.randomUUID(), product: null, quantity: 1 }];
	let quoteName = '';
	let editingQuoteName = false;
	let loading = false;
	let saving = false;
	let syncing = false;
	let error = '';
	let success = '';
	let shareUrl = '';
	let shareMenuOpen = false;
	let filterMenuOpen = false;
	let billingMenuOpen = false;
	let importModalOpen = false;
	let isDragging = false;
	let saveModalOpen = false;
	let editPassword = '';
	let confirmPassword = '';
	let passwordError = '';
	
	// Edit mode (editing existing quote)
	let editingQuoteId: string | null = null;
	let editQuotePassword: string | null = null;
	
	// Billing visibility toggles
	let showAnnual = true;
	let showMonthly = true;
	let showOnDemand = false;
	
	// Tools visibility
	let showLogsCalculator = false;
	
	// Filter products based on selected plan (show selected plan + "All" products)
	// Products without a plan field are treated as "All" (available to all plans)
	$: filteredProducts = products.filter(p => {
		const productPlan = p.plan || 'All';
		return productPlan === selectedPlan || productPlan === 'All';
	});

	$: lastSyncFormatted = metadata?.last_sync
		? new Date(metadata.last_sync).toLocaleString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric',
				hour: '2-digit',
				minute: '2-digit'
		  })
		: null;

	$: validLines = lines.filter((l) => l.product !== null);

	// Calculate total allotted quantity for each product from allotment lines
	function getTotalAllottedForProduct(productName: string | undefined): number {
		if (!productName) return 0;
		return lines
			.filter(l => l.isAllotment && l.product?.product === productName)
			.reduce((sum, l) => sum + (l.includedQuantity || 0), 0);
	}

	// Compute all billing totals simultaneously (considering allotments and percentage-based pricing)
	$: totals = (() => {
		// First pass: calculate base totals (non-percentage items)
		const baseTotals = validLines.reduce(
			(acc, line) => {
				if (!line.product) return acc;
				
				// Skip percentage-based products in first pass
				if (isPercentagePrice(line.product.billed_annually)) return acc;
				
				const annualPrice = parsePrice(line.product.billed_annually);
				const monthlyPrice = parsePrice(line.product.billed_month_to_month);
				const onDemandPrice = parsePrice(line.product.on_demand);
				
				// For allotments, only charge for quantity exceeding included amount
				const chargeableQty = line.isAllotment 
					? Math.max(0, line.quantity - (line.includedQuantity || 0))
					: line.quantity;
				
				return {
					annually: acc.annually + annualPrice * chargeableQty,
					monthly: acc.monthly + monthlyPrice * chargeableQty,
					on_demand: acc.on_demand + onDemandPrice * chargeableQty
				};
			},
			{ annually: 0, monthly: 0, on_demand: 0 }
		);
		
		// Second pass: calculate percentage-based add-ons
		const percentageAddOns = validLines.reduce(
			(acc, line) => {
				if (!line.product) return acc;
				
				// Only process percentage-based products
				if (!isPercentagePrice(line.product.billed_annually)) return acc;
				
				const annualPercent = parsePercentage(line.product.billed_annually);
				const monthlyPercent = parsePercentage(line.product.billed_month_to_month);
				const onDemandPercent = parsePercentage(line.product.on_demand);
				
				return {
					annually: acc.annually + (baseTotals.annually * annualPercent / 100),
					monthly: acc.monthly + (baseTotals.monthly * monthlyPercent / 100),
					on_demand: acc.on_demand + (baseTotals.on_demand * onDemandPercent / 100)
				};
			},
			{ annually: 0, monthly: 0, on_demand: 0 }
		);
		
		// Return total = base + percentage add-ons
		return {
			annually: baseTotals.annually + percentageAddOns.annually,
			monthly: baseTotals.monthly + percentageAddOns.monthly,
			on_demand: baseTotals.on_demand + percentageAddOns.on_demand
		};
	})();

	// Calculate annual costs for comparison
	$: annualCosts = {
		annually: totals.annually * 12,
		monthly: totals.monthly * 12,
		on_demand: totals.on_demand * 12
	};

	// Calculate savings between visible options
	$: savingsVsMonthly = annualCosts.monthly - annualCosts.annually;
	$: savingsVsOnDemand = annualCosts.on_demand - annualCosts.annually;
	$: savingsMonthlyVsOnDemand = annualCosts.on_demand - annualCosts.monthly;
	$: savingsPercentVsMonthly = annualCosts.monthly > 0 ? (savingsVsMonthly / annualCosts.monthly) * 100 : 0;
	$: savingsPercentVsOnDemand = annualCosts.on_demand > 0 ? (savingsVsOnDemand / annualCosts.on_demand) * 100 : 0;
	$: savingsPercentMonthlyVsOnDemand = annualCosts.on_demand > 0 ? (savingsMonthlyVsOnDemand / annualCosts.on_demand) * 100 : 0;

	// Determine best value and savings based on visible columns
	$: bestValueOption = (() => {
		const visible = [];
		if (showAnnual) visible.push({ key: 'annual', cost: annualCosts.annually });
		if (showMonthly) visible.push({ key: 'monthly', cost: annualCosts.monthly });
		if (showOnDemand) visible.push({ key: 'ondemand', cost: annualCosts.on_demand });
		if (visible.length < 2) return null;
		return visible.reduce((min, curr) => curr.cost < min.cost ? curr : min);
	})();

	$: worstValueOption = (() => {
		const visible = [];
		if (showAnnual) visible.push({ key: 'annual', cost: annualCosts.annually });
		if (showMonthly) visible.push({ key: 'monthly', cost: annualCosts.monthly });
		if (showOnDemand) visible.push({ key: 'ondemand', cost: annualCosts.on_demand });
		if (visible.length < 2) return null;
		return visible.reduce((max, curr) => curr.cost > max.cost ? curr : max);
	})();

	$: dynamicSavings = bestValueOption && worstValueOption && bestValueOption.key !== worstValueOption.key
		? worstValueOption.cost - bestValueOption.cost
		: 0;

	$: dynamicSavingsPercent = worstValueOption && worstValueOption.cost > 0
		? (dynamicSavings / worstValueOption.cost) * 100
		: 0;

	$: bestValueLabel = bestValueOption?.key === 'annual' ? 'annual' : bestValueOption?.key === 'monthly' ? 'monthly' : 'on-demand';
	$: worstValueLabel = worstValueOption?.key === 'annual' ? 'annual' : worstValueOption?.key === 'monthly' ? 'monthly' : 'on-demand';

	onMount(async () => {
		await loadRegions();
		await loadAllotments();
		await loadProducts();
		
		// Check for edit parameter (editing existing quote)
		const editParam = $page.url.searchParams.get('edit');
		if (editParam) {
			try {
				const editData = JSON.parse(decodeURIComponent(editParam));
				await loadEditQuote(editData);
				// Remove the edit param from URL
				goto('/', { replaceState: true });
			} catch (e) {
				console.error('Failed to parse edit data:', e);
			}
			return;
		}
		
		// Check for clone parameter
		const cloneParam = $page.url.searchParams.get('clone');
		if (cloneParam) {
			try {
				const cloneData = JSON.parse(decodeURIComponent(cloneParam));
				await loadClonedQuote(cloneData);
				// Remove the clone param from URL
				goto('/', { replaceState: true });
			} catch (e) {
				console.error('Failed to parse clone data:', e);
			}
		}
	});

	async function loadAllotments() {
		try {
			allotments = await fetchAllotments();
			if (allotments.length === 0) {
				// Initialize with manual allotments
				await initAllotments();
				allotments = await fetchAllotments();
			}
		} catch (e) {
			console.error('Failed to load allotments:', e);
		}
	}

	async function loadClonedQuote(cloneData: { name: string; items: { id?: string; product: string; quantity: number }[] }) {
		quoteName = cloneData.name ? `${cloneData.name} (Copy)` : '';
		
		// Map cloned items to lines - match by ID first, then by name
		const newLines: LineItem[] = [];
		for (const item of cloneData.items) {
			let matchedProduct = item.id 
				? products.find(p => p.id === item.id)
				: null;
			
			// Fallback to name matching if ID not found
			if (!matchedProduct) {
				matchedProduct = products.find(p => p.product === item.product);
			}
			
			if (matchedProduct) {
				newLines.push({
					id: crypto.randomUUID(),
					product: matchedProduct,
					quantity: item.quantity
				});
			}
		}
		
		if (newLines.length > 0) {
			lines = newLines;
			success = 'Quote cloned successfully! You can now edit it.';
			setTimeout(() => success = '', 5000);
		}
	}

	async function loadEditQuote(editData: { quoteId: string; name: string; region: string; editPassword: string | null; items: { id?: string; product: string; quantity: number }[] }) {
		// Store edit mode info
		editingQuoteId = editData.quoteId;
		editQuotePassword = editData.editPassword;
		quoteName = editData.name || '';
		
		// Change region if different
		if (editData.region && editData.region !== selectedRegion) {
			selectedRegion = editData.region;
			await loadProducts();
		}
		
		// Map items to lines - match by ID first, then by name
		const newLines: LineItem[] = [];
		for (const item of editData.items) {
			let matchedProduct = item.id 
				? products.find(p => p.id === item.id)
				: null;
			
			// Fallback to name matching if ID not found
			if (!matchedProduct) {
				matchedProduct = products.find(p => p.product === item.product);
			}
			
			if (matchedProduct) {
				newLines.push({
					id: crypto.randomUUID(),
					product: matchedProduct,
					quantity: item.quantity
				});
			}
		}
		
		if (newLines.length > 0) {
			lines = newLines;
			success = 'Editing quote. Make your changes and save.';
			setTimeout(() => success = '', 5000);
		}
	}

	async function loadRegions() {
		try {
			regions = await fetchRegions();
		} catch (e) {
			console.error('Failed to load regions:', e);
		}
	}

	async function loadProducts() {
		loading = true;
		error = '';
		try {
			[products, metadata] = await Promise.all([
				fetchProducts(selectedRegion),
				fetchMetadata(selectedRegion)
			]);
			// Sort products alphabetically by name
			products = products.sort((a, b) => a.product.localeCompare(b.product));
			if (products.length === 0) {
				error = 'No products found. Please wait for automatic sync or check backend connection.';
			}
		} catch (e) {
			error = 'Failed to load products. Make sure the backend is running.';
		} finally {
			loading = false;
		}
	}

	async function handleSync() {
		syncing = true;
		error = '';
		try {
			await syncPricing(selectedRegion);
			await loadProducts();
			success = 'Pricing data synced successfully!';
			setTimeout(() => success = '', 3000);
		} catch (e) {
			error = 'Failed to sync pricing data.';
		} finally {
			syncing = false;
		}
	}

	async function handleRegionChange() {
		// Reset metadata to show loading state
		metadata = null;
		
		// Store current line selections (product IDs and quantities)
		const previousSelections = lines.map(line => ({
			id: line.id,
			productId: line.product?.id || null,
			productName: line.product?.product || null,
			quantity: line.quantity,
			isAllotment: line.isAllotment,
			parentLineId: line.parentLineId,
			allotmentInfo: line.allotmentInfo,
			includedQuantity: line.includedQuantity
		}));
		
		// Load new region's products
		await loadProducts();
		
		// Restore line selections by matching product IDs to new region's products
		lines = previousSelections.map(selection => {
			// Match by ID first (IDs are consistent across regions)
			let matchedProduct = selection.productId 
				? products.find(p => p.id === selection.productId) || null
				: null;
			
			// Fallback to name matching
			if (!matchedProduct && selection.productName) {
				matchedProduct = products.find(p => p.product === selection.productName) || null;
			}
			
			return {
				id: selection.id,
				product: matchedProduct,
				quantity: selection.quantity,
				isAllotment: selection.isAllotment,
				parentLineId: selection.parentLineId,
				allotmentInfo: selection.allotmentInfo,
				includedQuantity: selection.includedQuantity
			};
		});
	}

	function addLine() {
		lines = [...lines, { id: crypto.randomUUID(), product: null, quantity: 1 }];
	}

	function addItemsFromCalculator(items: { product: Product; quantity: number }[]) {
		const newLines: LineItem[] = [];
		
		for (const item of items) {
			// Check if product already exists in lines
			const existingLine = lines.find(l => l.product?.id === item.product.id);
			if (existingLine) {
				// Update quantity
				lines = lines.map(l => 
					l.id === existingLine.id 
						? { ...l, quantity: l.quantity + item.quantity }
						: l
				);
			} else {
				// Add new line
				newLines.push({
					id: crypto.randomUUID(),
					product: item.product,
					quantity: item.quantity
				});
			}
		}
		
		if (newLines.length > 0) {
			// Remove empty lines first
			lines = lines.filter(l => l.product !== null);
			lines = [...lines, ...newLines];
			
			// If lines was empty, the new lines are already added
			if (lines.length === 0) {
				lines = newLines;
			}
		}
		
		// Close the calculator
		showLogsCalculator = false;
		success = `Added ${items.length} item(s) to quote`;
		setTimeout(() => success = '', 3000);
	}

	function removeLine(id: string) {
		// Remove the line and any associated allotment lines
		lines = lines.filter((l) => l.id !== id && l.parentLineId !== id);
		
		// If all lines were removed, add an empty one
		if (lines.length === 0) {
			lines = [{ id: crypto.randomUUID(), product: null, quantity: 1 }];
		}
	}

	function updateLine(id: string, product: Product | null, quantity: number) {
		const existingLine = lines.find(l => l.id === id);
		const previousProductId = existingLine?.product?.id;
		
		// Check if product changed (using ID for reliable comparison)
		const productChanged = product?.id !== previousProductId;
		
		// Build the new lines array in one go to avoid reactivity issues
		let newLines: LineItem[] = [];
		
		if (product && productChanged) {
			// Product changed: update line, remove old allotments, add new allotments
			
			// 1. Keep all lines except: the current line and its old allotments
			newLines = lines.filter(l => l.id !== id && l.parentLineId !== id);
			
			// 2. Add the updated line
			newLines.push({ ...existingLine!, product, quantity });
			
			// 3. Find and add new allotments for this product (match by product_id)
			// Deduplicate by allotted_product to avoid duplicate entries
			const productAllotmentsRaw = allotments.filter(a => 
				a.parent_product_id === product.id
			);
			const seenAllotments = new Set<string>();
			const productAllotments = productAllotmentsRaw.filter(a => {
				const key = a.allotted_product;
				if (seenAllotments.has(key)) return false;
				seenAllotments.add(key);
				return true;
			});
			
			for (const allotment of productAllotments) {
				// Match allotted product by ID first, then fallback to name
				const allottedProduct = products.find(p => 
					p.id === allotment.allotted_product_id
				) || products.find(p =>
					p.product.toLowerCase().includes(allotment.allotted_product.toLowerCase())
				);
				
				if (allottedProduct) {
					const includedQty = allotment.quantity_per_parent * quantity;
					newLines.push({
						id: crypto.randomUUID(),
						product: allottedProduct,
						quantity: includedQty,
						isAllotment: true,
						parentLineId: id,
						allotmentInfo: allotment,
						includedQuantity: includedQty
					});
				}
			}
		} else if (!productChanged && quantity !== existingLine?.quantity) {
			// Only quantity changed: update line and recalculate allotment quantities
			newLines = lines.map(l => {
				if (l.id === id) {
					return { ...l, product, quantity };
				}
				if (l.parentLineId === id && l.allotmentInfo) {
					const newIncluded = l.allotmentInfo.quantity_per_parent * quantity;
					return { ...l, includedQuantity: newIncluded };
				}
				return l;
			});
		} else {
			// Just update the line (no product change, no quantity change worth recalculating)
			newLines = lines.map((l) => (l.id === id ? { ...l, product, quantity } : l));
		}
		
		// Single assignment to trigger reactivity once
		lines = newLines;
	}

	function openSaveModal() {
		if (validLines.length === 0) {
			error = 'Please add at least one product to share';
			return;
		}
		
		// If editing an existing quote, save directly without modal
		if (editingQuoteId) {
			handleShare();
			shareMenuOpen = false;
			return;
		}
		
		editPassword = '';
		confirmPassword = '';
		passwordError = '';
		saveModalOpen = true;
		shareMenuOpen = false;
	}

	async function handleShare() {
		// Validate passwords match if provided (only for new quotes)
		if (!editingQuoteId && editPassword && editPassword !== confirmPassword) {
			passwordError = 'Passwords do not match';
			return;
		}

		saving = true;
		error = '';
		passwordError = '';

		try {
			// Build items with allotment info and product IDs
			const items = validLines
				.filter(l => !l.isAllotment) // Only parent products
				.map((l) => {
					// Find allotments for this line
					const lineAllotments = lines
						.filter(al => al.isAllotment && al.parentLineId === l.id)
						.map(al => ({
							id: al.product!.id,
							allotted_product: al.product!.product,
							quantity_included: al.includedQuantity || 0,
							allotted_unit: al.allotmentInfo?.allotted_unit || 'units'
						}));
					
					return {
						id: l.product!.id,
						product: l.product!.product,
						quantity: l.quantity,
						allotments: lineAllotments
					};
				});

			let quote;
			if (editingQuoteId) {
				// Update existing quote
				quote = await updateQuote(editingQuoteId, quoteName || null, selectedRegion, 'annually', items, editQuotePassword);
				shareUrl = `${window.location.origin}/quote/${quote.id}`;
				saveModalOpen = false;
				success = 'Quote updated successfully!';
				// Keep edit mode active so user can continue making changes
			} else {
				// Create new quote
				quote = await createQuote(quoteName || null, selectedRegion, 'annually', items, editPassword || null);
				shareUrl = `${window.location.origin}/quote/${quote.id}`;
				saveModalOpen = false;
				success = quote.is_protected ? 'Quote saved with password protection!' : 'Quote saved!';
			}
			setTimeout(() => success = '', 3000);
		} catch (e: any) {
			error = e.message || 'Failed to save quote';
		} finally {
			saving = false;
		}
	}

	function copyShareUrl() {
		navigator.clipboard.writeText(shareUrl);
		success = 'URL copied to clipboard!';
		shareMenuOpen = false;
		setTimeout(() => success = '', 3000);
	}

	function downloadPDF() {
		// Create a printable version
		const printContent = generatePrintContent();
		const printWindow = window.open('', '_blank');
		if (printWindow) {
			printWindow.document.write(printContent);
			printWindow.document.close();
			printWindow.onload = () => {
				printWindow.print();
			};
		}
		shareMenuOpen = false;
	}

	function downloadCSV() {
		const headers = ['Product', 'Billing Unit', 'Quantity', 'Annual (Monthly)', 'Monthly (Monthly)', 'On-Demand (Monthly)', 'Annual (Yearly)', 'Monthly (Yearly)', 'On-Demand (Yearly)'];
		
		const rows = validLines.map(line => [
			`"${line.product?.product || ''}"`,
			`"${line.product?.billing_unit || ''}"`,
			line.quantity,
			parsePrice(line.product?.billed_annually) * line.quantity,
			parsePrice(line.product?.billed_month_to_month) * line.quantity,
			parsePrice(line.product?.on_demand) * line.quantity,
			parsePrice(line.product?.billed_annually) * line.quantity * 12,
			parsePrice(line.product?.billed_month_to_month) * line.quantity * 12,
			parsePrice(line.product?.on_demand) * line.quantity * 12
		]);

		// Add totals row
		rows.push([
			'"TOTAL"',
			'""',
			'',
			totals.annually,
			totals.monthly,
			totals.on_demand,
			annualCosts.annually,
			annualCosts.monthly,
			annualCosts.on_demand
		]);

		const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
		
		const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
		const link = document.createElement('a');
		const url = URL.createObjectURL(blob);
		link.setAttribute('href', url);
		link.setAttribute('download', `datadog-quote${quoteName ? '-' + quoteName.replace(/\s+/g, '-') : ''}.csv`);
		link.style.visibility = 'hidden';
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		
		shareMenuOpen = false;
		success = 'CSV exported successfully!';
		setTimeout(() => success = '', 3000);
	}

	function generatePrintContent() {
		const date = new Date().toLocaleDateString('en-US', { 
			year: 'numeric', 
			month: 'long', 
			day: 'numeric' 
		});
		
		const rows = validLines.map(line => `
			<tr>
				<td style="padding: 12px; border-bottom: 1px solid #e5e5e5;">${line.product?.product}</td>
				<td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: center;">${line.quantity}</td>
				<td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; color: #3ecfa8;">${formatCurrency(parsePrice(line.product?.billed_annually) * line.quantity)}</td>
				<td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; color: #632ca6;">${formatCurrency(parsePrice(line.product?.billed_month_to_month) * line.quantity)}</td>
				<td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; color: #ff6f00;">${formatCurrency(parsePrice(line.product?.on_demand) * line.quantity)}</td>
			</tr>
		`).join('');

		return `
			<!DOCTYPE html>
			<html>
			<head>
				<title>PriceHound Quote${quoteName ? ` - ${quoteName}` : ''}</title>
				<style>
					body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; color: #333; }
					h1 { color: #632ca6; margin-bottom: 8px; }
					.date { color: #666; margin-bottom: 32px; }
					table { width: 100%; border-collapse: collapse; margin-bottom: 32px; }
					th { background: #f5f5f5; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
					.totals { display: flex; gap: 24px; margin-bottom: 32px; }
					.total-card { flex: 1; padding: 20px; border-radius: 12px; }
					.total-card.annual { background: rgba(62, 207, 168, 0.1); border: 1px solid rgba(62, 207, 168, 0.3); }
					.total-card.monthly { background: rgba(99, 44, 166, 0.1); border: 1px solid rgba(99, 44, 166, 0.3); }
					.total-card.ondemand { background: rgba(255, 111, 0, 0.1); border: 1px solid rgba(255, 111, 0, 0.3); }
					.total-label { font-size: 14px; color: #666; margin-bottom: 8px; }
					.total-value { font-size: 24px; font-weight: bold; }
					.total-card.annual .total-value { color: #3ecfa8; }
					.total-card.monthly .total-value { color: #632ca6; }
					.total-card.ondemand .total-value { color: #ff6f00; }
					.savings { background: linear-gradient(135deg, rgba(62, 207, 168, 0.1), rgba(99, 44, 166, 0.1)); padding: 20px; border-radius: 12px; }
					.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e5; color: #666; font-size: 12px; }
					@media print { body { padding: 20px; } }
				</style>
			</head>
			<body>
				<h1>PriceHound Quote${quoteName ? `: ${quoteName}` : ''}</h1>
				<p class="date">Generated on ${date}</p>
				
				<table>
					<thead>
						<tr>
							<th>Product</th>
							<th style="text-align: center;">Qty</th>
							<th style="text-align: right;">Annual</th>
							<th style="text-align: right;">Monthly</th>
							<th style="text-align: right;">On-Demand</th>
						</tr>
					</thead>
					<tbody>
						${rows}
					</tbody>
					<tfoot>
						<tr style="font-weight: bold;">
							<td style="padding: 12px;" colspan="2">Monthly Total</td>
							<td style="padding: 12px; text-align: right; color: #3ecfa8;">${formatCurrency(totals.annually)}</td>
							<td style="padding: 12px; text-align: right; color: #632ca6;">${formatCurrency(totals.monthly)}</td>
							<td style="padding: 12px; text-align: right; color: #ff6f00;">${formatCurrency(totals.on_demand)}</td>
						</tr>
						<tr style="color: #666;">
							<td style="padding: 12px;" colspan="2">Annual Cost (×12)</td>
							<td style="padding: 12px; text-align: right;">${formatCurrency(annualCosts.annually)}</td>
							<td style="padding: 12px; text-align: right;">${formatCurrency(annualCosts.monthly)}</td>
							<td style="padding: 12px; text-align: right;">${formatCurrency(annualCosts.on_demand)}</td>
						</tr>
					</tfoot>
				</table>

				<div class="totals">
					<div class="total-card annual">
						<div class="total-label">Billed Annually</div>
						<div class="total-value">${formatCurrency(totals.annually)}/mo</div>
						<div style="color: #666; font-size: 14px;">${formatCurrency(annualCosts.annually)}/year</div>
					</div>
					<div class="total-card monthly">
						<div class="total-label">Billed Monthly</div>
						<div class="total-value">${formatCurrency(totals.monthly)}/mo</div>
						<div style="color: #666; font-size: 14px;">${formatCurrency(annualCosts.monthly)}/year</div>
					</div>
					<div class="total-card ondemand">
						<div class="total-label">On-Demand</div>
						<div class="total-value">${formatCurrency(totals.on_demand)}/mo</div>
						<div style="color: #666; font-size: 14px;">${formatCurrency(annualCosts.on_demand)}/year</div>
					</div>
				</div>

				${savingsVsOnDemand > 0 ? `
					<div class="savings">
						<strong>Potential Annual Savings:</strong> ${formatCurrency(savingsVsOnDemand)} per year (${savingsPercentVsOnDemand.toFixed(1)}% savings) by choosing annual billing over on-demand.
					</div>
				` : ''}

				<div class="footer">
					<p>Pricing data sourced from datadoghq.com/pricing/list/</p>
					${shareUrl ? `<p>Quote URL: ${shareUrl}</p>` : ''}
				</div>
			</body>
			</html>
		`;
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.share-menu-container')) {
			shareMenuOpen = false;
		}
		if (!target.closest('.filter-menu-container')) {
			filterMenuOpen = false;
		}
		if (!target.closest('.billing-menu-container')) {
			billingMenuOpen = false;
		}
	}

	function exportJSON() {
		const exportData = {
			name: quoteName || 'PriceHound Quote',
			region: selectedRegion,
			plan: selectedPlan,
			created_at: new Date().toISOString(),
			items: validLines
				.filter(l => !l.isAllotment)
				.map(line => {
					const lineAllotments = lines
						.filter(al => al.isAllotment && al.parentLineId === line.id)
						.map(al => ({
							id: al.product?.id || '',
							product: al.product?.product || '',
							quantity_included: al.includedQuantity || 0,
							unit: al.allotmentInfo?.allotted_unit || 'units'
						}));
					
					return {
						id: line.product?.id || '',
						product: line.product?.product || '',
						billing_unit: line.product?.billing_unit || '',
						quantity: line.quantity,
						prices: {
							annual: line.product?.billed_annually || '',
							monthly: line.product?.billed_month_to_month || '',
							on_demand: line.product?.on_demand || ''
						},
						allotments: lineAllotments
					};
				}),
			totals: {
				monthly: totals,
				yearly: annualCosts
			}
		};

		const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `pricehound-quote-${new Date().toISOString().split('T')[0]}.json`;
		link.style.visibility = 'hidden';
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
		
		shareMenuOpen = false;
		success = 'JSON exported successfully!';
		setTimeout(() => success = '', 3000);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
		
		const files = event.dataTransfer?.files;
		if (files && files.length > 0) {
			processImportFile(files[0]);
		}
	}

	function handleFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			processImportFile(input.files[0]);
		}
	}

	async function processImportFile(file: File) {
		if (!file.name.endsWith('.json')) {
			error = 'Please select a JSON file';
			return;
		}

		try {
			const text = await file.text();
			const data = JSON.parse(text);
			
			// Validate structure
			if (!data.items || !Array.isArray(data.items)) {
				error = 'Invalid JSON format: missing items array';
				return;
			}

			// Set quote name if present
			if (data.name) {
				quoteName = data.name;
			}

			// Set plan if present and valid
			if (data.plan && ['Pro', 'Enterprise'].includes(data.plan)) {
				selectedPlan = data.plan;
			}

			// Set region if present and valid
			if (data.region && ['us', 'us1-fed', 'eu1', 'ap1', 'ap2'].includes(data.region)) {
				if (data.region !== selectedRegion) {
					selectedRegion = data.region;
					await loadProducts();
				}
			}

			// Make sure products are loaded
			if (products.length === 0) {
				await loadProducts();
			}

			// Also load allotments if not already loaded
			if (allotments.length === 0) {
				await loadAllotments();
			}

			// Clear existing lines
			lines = [];

			// Import items one by one and trigger allotment loading
			for (const item of data.items) {
				if (!item.product && !item.id) continue;
				
				// Find matching product - try by ID first, then by name
				let matchingProduct = item.id 
					? products.find(p => p.id === item.id)
					: null;
				
				// Fallback to name matching if ID not found
				if (!matchingProduct) {
					matchingProduct = products.find(p => p.product === item.product);
				}
				
				if (!matchingProduct) {
					console.warn(`Product not found: ${item.product} (id: ${item.id})`);
					continue;
				}
				
				const lineId = crypto.randomUUID();
				const newLine: LineItem = {
					id: lineId,
					product: matchingProduct,
					quantity: item.quantity || 1,
					isAllotment: false
				};
				
				lines = [...lines, newLine];
				
				// Find and add allotments for this product (match by product_id)
				// Deduplicate by allotted_product to avoid duplicate entries
				const productAllotmentsRaw = allotments.filter(a => 
					a.parent_product_id === matchingProduct.id
				);
				const seenAllotments = new Set<string>();
				const productAllotments = productAllotmentsRaw.filter(a => {
					const key = a.allotted_product;
					if (seenAllotments.has(key)) return false;
					seenAllotments.add(key);
					return true;
				});
				
				for (const allotment of productAllotments) {
					// Match allotted product by ID first, then fallback to name
					const allottedProduct = products.find(p => 
						p.id === allotment.allotted_product_id
					) || products.find(p =>
						p.product.toLowerCase().includes(allotment.allotted_product.toLowerCase())
					);
					
					if (allottedProduct) {
						const includedQty = allotment.quantity_per_parent * (item.quantity || 1);
						const allotmentLine: LineItem = {
							id: crypto.randomUUID(),
							product: allottedProduct,
							quantity: includedQty,
							isAllotment: true,
							parentLineId: lineId,
							allotmentInfo: allotment,
							includedQuantity: includedQty
						};
						lines = [...lines, allotmentLine];
					}
				}
			}

			importModalOpen = false;
			success = `Imported ${data.items.length} products successfully!`;
			setTimeout(() => success = '', 3000);
		} catch (e) {
			error = 'Failed to parse JSON file';
		}
	}
</script>

<svelte:head>
	<title>PriceHound - Datadog Usage Forecaster</title>
</svelte:head>

<svelte:window on:click={handleClickOutside} />

<div class="container mx-auto max-w-7xl px-4 py-8">
	<!-- Header -->
	<header class="mb-8">
		<!-- Title and Tagline (centered) -->
		<div class="text-center mb-6">
			<div class="mb-2 inline-flex items-center gap-3">
				<div class="flex h-12 w-12 items-center justify-center rounded-xl bg-datadog-purple shadow-lg shadow-datadog-purple/30">
					<svg class="h-7 w-7 text-white" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12.13 2C6.54 2 2 6.54 2 12.13c0 5.59 4.54 10.13 10.13 10.13 5.59 0 10.13-4.54 10.13-10.13C22.26 6.54 17.72 2 12.13 2zm5.41 14.35c-.31.31-.82.31-1.13 0l-3.07-3.07-1.17 1.17 3.07 3.07c.31.31.31.82 0 1.13-.31.31-.82.31-1.13 0l-3.07-3.07-1.93 1.93c-.31.31-.82.31-1.13 0-.31-.31-.31-.82 0-1.13l1.93-1.93-3.07-3.07c-.31-.31-.31-.82 0-1.13.31-.31.82-.31 1.13 0l3.07 3.07 1.17-1.17-3.07-3.07c-.31-.31-.31-.82 0-1.13.31-.31.82-.31 1.13 0l3.07 3.07 1.93-1.93c.31-.31.82-.31 1.13 0 .31.31.31.82 0 1.13l-1.93 1.93 3.07 3.07c.31.31.31.82 0 1.13z"/>
					</svg>
				</div>
				<h1 class="text-4xl font-bold tracking-tight">
					<span class="text-datadog-purple">Price</span>Hound
				</h1>
			</div>
			<p class="text-sm text-muted-foreground">
				Get a sense of your Datadog costs before you commit.
			</p>
		</div>

	</header>

	<!-- Unified Toolbar -->
	<div class="mb-6 rounded-xl border border-border bg-card/50 p-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<!-- Left: Region & Info -->
			<div class="flex items-center gap-3">
				<!-- Region Selector -->
				<div class="flex items-center gap-2">
					<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10" />
						<path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
					</svg>
					<select
						bind:value={selectedRegion}
						on:change={handleRegionChange}
						class="h-8 rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-datadog-purple cursor-pointer"
					>
						{#each Object.entries(regions) as [id, region]}
							<option value={id}>{region.name}</option>
						{/each}
					</select>
				</div>

				<!-- Separator -->
				<div class="h-6 w-px bg-border"></div>

				<!-- Pricing Info & Sync Button -->
				<div class="flex items-center gap-2">
					<div class="text-xs text-muted-foreground hidden sm:block">
						{#if loading}
							<span class="text-muted-foreground/50">Loading...</span>
						{:else if products.length > 0}
							<span>{products.length} products</span>
							{#if lastSyncFormatted}
								<span class="mx-1">·</span>
								<span>Updated: {lastSyncFormatted}</span>
							{/if}
						{/if}
					</div>
					<button
						type="button"
						on:click={handleSync}
						disabled={syncing}
						class="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
						title="Sync pricing data now"
					>
						<svg class="h-4 w-4 {syncing ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
					</button>
				</div>
			</div>

			<!-- Right: Button Group -->
			<div class="inline-flex items-center rounded-lg border border-input bg-background">
				<!-- Import Button -->
				<button
					type="button"
					on:click={() => importModalOpen = true}
					class="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors hover:bg-muted border-r border-input rounded-l-lg"
				>
					<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 3v12" />
					</svg>
					<span class="hidden sm:inline">Import</span>
				</button>

				<!-- Share Button with Dropdown -->
				<div class="share-menu-container relative">
					<button
						type="button"
						on:click={() => shareMenuOpen = !shareMenuOpen}
						disabled={validLines.length === 0}
						class="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed bg-datadog-purple text-white hover:bg-datadog-purple/90 rounded-r-lg"
					>
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13" />
						</svg>
						<span class="hidden sm:inline">Share</span>
						<svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M6 9l6 6 6-6" />
						</svg>
					</button>

					<!-- Dropdown Menu -->
					{#if shareMenuOpen}
						<div class="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border bg-card p-2 shadow-2xl z-50">
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={openSaveModal}
								disabled={saving}
							>
								{#if saving}
									<svg class="h-4 w-4 animate-spin text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M21 12a9 9 0 11-6.219-8.56" />
									</svg>
								{:else if editingQuoteId}
									<svg class="h-4 w-4 text-datadog-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
										<polyline points="17 21 17 13 7 13 7 21" />
										<polyline points="7 3 7 8 15 8" />
									</svg>
								{:else}
									<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
										<path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
									</svg>
								{/if}
								<span>{saving ? 'Saving...' : editingQuoteId ? 'Save Changes' : 'Create Public URL'}</span>
							</button>
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={downloadCSV}
							>
								<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
									<polyline points="14 2 14 8 20 8" />
									<path d="M8 13h2M8 17h2M14 13h2M14 17h2" />
								</svg>
								<span>Export CSV</span>
							</button>
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={exportJSON}
							>
								<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
									<polyline points="14 2 14 8 20 8" />
									<path d="M10 12l-2 2 2 2M14 12l2 2-2 2" />
								</svg>
								<span>Export JSON</span>
							</button>
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={downloadPDF}
							>
								<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
									<polyline points="14 2 14 8 20 8" />
									<line x1="12" y1="18" x2="12" y2="12" />
									<line x1="9" y1="15" x2="15" y2="15" />
								</svg>
								<span>Download PDF</span>
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>


	<!-- Alerts -->
	{#if error}
		<div class="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
			{error}
		</div>
	{/if}

	{#if success}
		<div class="mb-6 rounded-lg border border-datadog-green/50 bg-datadog-green/10 p-4 text-datadog-green">
			{success}
		</div>
	{/if}

	<!-- Edit Mode Banner -->
	{#if editingQuoteId}
		<div class="mb-4 flex items-center gap-3 rounded-lg border border-datadog-green/50 bg-datadog-green/10 px-4 py-3">
			<svg class="h-5 w-5 text-datadog-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
				<path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
			</svg>
			<div class="flex-1">
				<span class="font-medium text-datadog-green">Editing Quote</span>
				<span class="text-sm text-muted-foreground ml-2">Make your changes and click Save to update</span>
			</div>
			<button
				type="button"
				class="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted transition-colors"
				on:click={() => { const id = editingQuoteId; editingQuoteId = null; editQuotePassword = null; goto(`/quote/${id}`); }}
			>
				Cancel
			</button>
		</div>
	{/if}

	<!-- Share URL Display -->
	{#if shareUrl}
		<div class="mb-4 flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
			<span class="text-sm text-muted-foreground">Public URL:</span>
			<a 
				href={shareUrl} 
				target="_blank"
				class="flex-1 truncate font-mono text-sm text-datadog-purple hover:underline"
			>
				{shareUrl}
			</a>
			<button
				type="button"
				class="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={copyShareUrl}
				title="Copy URL"
			>
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="9" y="9" width="13" height="13" rx="2" />
					<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
				</svg>
			</button>
			<button
				type="button"
				class="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={() => shareUrl = ''}
				title="Dismiss"
			>
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>
		</div>
	{/if}

	<!-- Quote Lines -->
	<Card class="mb-6 overflow-visible relative z-10">
		<CardHeader>
			<div class="flex flex-wrap items-start justify-between gap-4">
				<div class="flex items-center gap-3">
					<div class="flex h-11 w-11 items-center justify-center rounded-xl bg-datadog-purple shadow-lg shadow-datadog-purple/30">
						<svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="9" cy="21" r="1" />
							<circle cx="20" cy="21" r="1" />
							<path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6" />
						</svg>
					</div>
					<div>
						{#if editingQuoteName}
							<input
								bind:value={quoteName}
								placeholder="Enter quote name..."
								class="text-lg font-semibold h-8 px-2 rounded border border-input bg-background focus:outline-none focus:ring-2 focus:ring-datadog-purple"
								autofocus
								on:blur={() => editingQuoteName = false}
								on:keydown={(e) => { if (e.key === 'Enter' || e.key === 'Escape') editingQuoteName = false; }}
							/>
						{:else}
							<!-- svelte-ignore a11y-click-events-have-key-events -->
							<!-- svelte-ignore a11y-no-static-element-interactions -->
							<div 
								class="group flex items-center gap-2 cursor-pointer"
								on:click={() => editingQuoteName = true}
							>
								<CardTitle class="group-hover:text-datadog-purple transition-colors">
									{quoteName || 'Quote Items'}
								</CardTitle>
								<svg class="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
									<path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
								</svg>
							</div>
						{/if}
						<CardDescription>Add products and specify quantities</CardDescription>
					</div>
				</div>
				
				<!-- Plan & Billing Selectors Group -->
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div class="inline-flex items-center rounded-lg border border-input bg-background" on:click|stopPropagation>
					<!-- Plan Selector (Left) -->
					<div class="inline-flex items-center p-1 border-r border-input">
						<button
							type="button"
							class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {selectedPlan === 'Pro' ? 'bg-datadog-purple text-white' : 'hover:bg-muted'}"
							on:click={() => selectedPlan = 'Pro'}
						>
							Pro
						</button>
						<button
							type="button"
							class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {selectedPlan === 'Enterprise' ? 'bg-datadog-purple text-white' : 'hover:bg-muted'}"
							on:click={() => selectedPlan = 'Enterprise'}
						>
							Enterprise
						</button>
					</div>
					
					<!-- Billing Dropdown (Right) -->
					<div class="relative billing-menu-container">
						<button
							type="button"
							on:click={() => billingMenuOpen = !billingMenuOpen}
							class="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors hover:bg-muted rounded-r-lg"
						>
							<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
							</svg>
							<span>Billing</span>
							<div class="flex items-center gap-0.5">
								{#if showAnnual}<span class="w-2 h-2 rounded-full bg-datadog-green"></span>{/if}
								{#if showMonthly}<span class="w-2 h-2 rounded-full bg-datadog-blue"></span>{/if}
								{#if showOnDemand}<span class="w-2 h-2 rounded-full bg-datadog-orange"></span>{/if}
							</div>
						</button>

						{#if billingMenuOpen}
							<div class="absolute right-0 top-full mt-2 w-48 rounded-xl border border-border bg-card p-2 shadow-2xl z-50">
								<button
									type="button"
									class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
									on:click={() => showAnnual = !showAnnual}
								>
									<span class="w-4 h-4 rounded border flex items-center justify-center {showAnnual ? 'bg-datadog-green border-datadog-green' : 'border-muted-foreground/30'}">
										{#if showAnnual}
											<svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
												<path d="M20 6L9 17l-5-5" />
											</svg>
										{/if}
									</span>
									<span class="text-datadog-green font-medium">Annually</span>
								</button>
								<button
									type="button"
									class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
									on:click={() => showMonthly = !showMonthly}
								>
									<span class="w-4 h-4 rounded border flex items-center justify-center {showMonthly ? 'bg-datadog-blue border-datadog-blue' : 'border-muted-foreground/30'}">
										{#if showMonthly}
											<svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
												<path d="M20 6L9 17l-5-5" />
											</svg>
										{/if}
									</span>
									<span class="text-datadog-blue font-medium">Monthly</span>
								</button>
								<button
									type="button"
									class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
									on:click={() => showOnDemand = !showOnDemand}
								>
									<span class="w-4 h-4 rounded border flex items-center justify-center {showOnDemand ? 'bg-datadog-orange border-datadog-orange' : 'border-muted-foreground/30'}">
										{#if showOnDemand}
											<svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
												<path d="M20 6L9 17l-5-5" />
											</svg>
										{/if}
									</span>
									<span class="text-datadog-orange font-medium">On-Demand</span>
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</CardHeader>
		<CardContent>
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<svg class="h-8 w-8 animate-spin text-datadog-purple" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 12a9 9 0 11-6.219-8.56" />
					</svg>
				</div>
			{:else}
				<div class="space-y-3 overflow-visible">
					{#each lines.filter(l => !l.isAllotment) as line, index (line.id)}
						{@const lineAllotments = lines.filter(l => l.isAllotment && l.parentLineId === line.id).map(l => ({
							product: l.product,
							includedQuantity: l.includedQuantity || 0,
							allotmentInfo: l.allotmentInfo || null
						}))}
						<QuoteLine
							products={filteredProducts}
							{index}
							{showAnnual}
							{showMonthly}
							{showOnDemand}
							selectedProduct={line.product}
							quantity={line.quantity}
							isAllotment={false}
							includedQuantity={0}
							allotmentInfo={null}
							totalAllottedForProduct={getTotalAllottedForProduct(line.product?.product)}
							{lineAllotments}
							on:update={(e) => updateLine(line.id, e.detail.product, e.detail.quantity)}
							on:remove={() => removeLine(line.id)}
						/>
					{/each}
				</div>

				<div class="mt-4 inline-flex w-full rounded-lg border-2 border-dashed border-border hover:border-foreground/30 transition-all">
					<button
						type="button"
						class="flex-1 inline-flex items-center justify-center gap-2 py-5 text-sm font-semibold transition-colors hover:bg-muted rounded-l-md"
						on:click={addLine}
					>
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
							<path d="M12 5v14M5 12h14" />
						</svg>
						Add Product
					</button>
					<button
						type="button"
						class="inline-flex items-center justify-center gap-2 px-3 py-3 text-xs font-medium transition-colors border-l-2 border-dashed border-border rounded-r-md {showLogsCalculator ? 'bg-datadog-purple text-white hover:bg-datadog-purple/90' : 'hover:bg-muted'}"
						on:click={() => showLogsCalculator = !showLogsCalculator}
						title="Log Indexing Estimator"
					>
						<svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
							<polyline points="14 2 14 8 20 8" />
							<line x1="16" y1="13" x2="8" y2="13" />
							<line x1="16" y1="17" x2="8" y2="17" />
						</svg>
						<span class="hidden sm:flex flex-col leading-tight text-center">
							<span>Log Indexing</span>
							<span>Estimator</span>
						</span>
					</button>
				</div>
			{/if}
		</CardContent>
	</Card>

	<!-- Summary Section -->
	{#if validLines.length > 0}
		<Card class="mb-6 relative z-0">
			<CardHeader>
				<div class="flex items-center gap-3">
					<div class="flex h-11 w-11 items-center justify-center rounded-xl bg-datadog-purple shadow-lg shadow-datadog-purple/30">
						<svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
						</svg>
					</div>
					<div>
						<CardTitle>Pricing Summary</CardTitle>
						<CardDescription>Compare costs across all billing options</CardDescription>
					</div>
				</div>
			</CardHeader>
			<CardContent>
				<!-- Totals Grid -->
				<div class="grid gap-4 mb-6" style="grid-template-columns: repeat({[showAnnual, showMonthly, showOnDemand].filter(Boolean).length}, 1fr);">
					{#if showAnnual}
						<!-- Annual -->
						<div class="relative rounded-xl border-2 border-datadog-green/50 bg-datadog-green/10 p-5 shadow-lg shadow-datadog-green/10">
							{#if bestValueOption?.key === 'annual' && dynamicSavings > 0}
								<div class="absolute -top-2.5 right-3 rounded-full bg-datadog-green px-2.5 py-0.5 text-xs font-bold text-white shadow">
									Best Value
								</div>
							{/if}
							<div class="text-sm font-medium text-datadog-green mb-2">Billed Annually</div>
							<div class="text-3xl font-bold text-datadog-green mb-1">
								{formatCurrency(annualCosts.annually)}
								<span class="text-sm font-normal text-muted-foreground">/year</span>
							</div>
							<div class="text-sm text-muted-foreground mb-3">
								{formatCurrency(totals.annually)}/month
							</div>
							{#if bestValueOption?.key === 'annual' && dynamicSavings > 0}
								<div class="flex items-center gap-1.5 text-sm font-medium text-datadog-green">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 5v14M5 12l7 7 7-7" />
									</svg>
									Save {formatCurrency(dynamicSavings)}/yr
								</div>
							{:else if bestValueOption && bestValueOption.key !== 'annual'}
								<div class="flex items-center gap-1.5 text-sm text-muted-foreground">
									<svg class="h-4 w-4 text-datadog-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 19V5M5 12l7-7 7 7" />
									</svg>
									+{((annualCosts.annually - bestValueOption.cost) / bestValueOption.cost * 100).toFixed(0)}% vs {bestValueLabel}
								</div>
							{/if}
						</div>
					{/if}

					{#if showMonthly}
						<!-- Monthly -->
						<div class="relative rounded-xl border border-datadog-blue/30 bg-datadog-blue/5 p-5">
							{#if bestValueOption?.key === 'monthly' && dynamicSavings > 0}
								<div class="absolute -top-2.5 right-3 rounded-full bg-datadog-blue px-2.5 py-0.5 text-xs font-bold text-white shadow">
									Best Value
								</div>
							{/if}
							<div class="text-sm font-medium text-datadog-blue mb-2">Billed Monthly</div>
							<div class="text-3xl font-bold text-datadog-blue mb-1">
								{formatCurrency(annualCosts.monthly)}
								<span class="text-sm font-normal text-muted-foreground">/year</span>
							</div>
							<div class="text-sm text-muted-foreground mb-3">
								{formatCurrency(totals.monthly)}/month
							</div>
							{#if bestValueOption?.key === 'monthly' && dynamicSavings > 0}
								<div class="flex items-center gap-1.5 text-sm font-medium text-datadog-blue">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 5v14M5 12l7 7 7-7" />
									</svg>
									Save {formatCurrency(dynamicSavings)}/yr
								</div>
							{:else if bestValueOption && bestValueOption.key !== 'monthly'}
								<div class="flex items-center gap-1.5 text-sm text-muted-foreground">
									<svg class="h-4 w-4 text-datadog-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 19V5M5 12l7-7 7 7" />
									</svg>
									+{((annualCosts.monthly - bestValueOption.cost) / bestValueOption.cost * 100).toFixed(0)}% vs {bestValueLabel}
								</div>
							{/if}
						</div>
					{/if}

					{#if showOnDemand}
						<!-- On-Demand -->
						<div class="relative rounded-xl border border-datadog-orange/30 bg-datadog-orange/5 p-5">
							{#if bestValueOption?.key === 'ondemand' && dynamicSavings > 0}
								<div class="absolute -top-2.5 right-3 rounded-full bg-datadog-orange px-2.5 py-0.5 text-xs font-bold text-white shadow">
									Best Value
								</div>
							{/if}
							<div class="text-sm font-medium text-datadog-orange mb-2">On-Demand</div>
							<div class="text-3xl font-bold text-datadog-orange mb-1">
								{formatCurrency(annualCosts.on_demand)}
								<span class="text-sm font-normal text-muted-foreground">/year</span>
							</div>
							<div class="text-sm text-muted-foreground mb-3">
								{formatCurrency(totals.on_demand)}/month
							</div>
							{#if bestValueOption?.key === 'ondemand' && dynamicSavings > 0}
								<div class="flex items-center gap-1.5 text-sm font-medium text-datadog-orange">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 5v14M5 12l7 7 7-7" />
									</svg>
									Save {formatCurrency(dynamicSavings)}/yr
								</div>
							{:else if bestValueOption && bestValueOption.key !== 'ondemand'}
								<div class="flex items-center gap-1.5 text-sm text-muted-foreground">
									<svg class="h-4 w-4 text-destructive" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 19V5M5 12l7-7 7 7" />
									</svg>
									+{((annualCosts.on_demand - bestValueOption.cost) / bestValueOption.cost * 100).toFixed(0)}% vs {bestValueLabel}
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Savings Highlight -->
				{#if dynamicSavings > 0 && bestValueOption && worstValueOption}
					<div class="rounded-xl bg-gradient-to-r from-datadog-green/15 to-datadog-purple/15 border border-datadog-green/20 p-5">
						<div class="flex flex-wrap items-center justify-between gap-4">
							<div class="flex items-center gap-3">
								<div class="flex h-12 w-12 items-center justify-center rounded-full bg-datadog-green/20">
									<svg class="h-6 w-6 text-datadog-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
									</svg>
								</div>
								<div>
									<div class="text-lg font-semibold">Potential Annual Savings</div>
									<div class="text-sm text-muted-foreground">By choosing {bestValueLabel} billing over {worstValueLabel}</div>
								</div>
							</div>
							<div class="text-right">
								<div class="text-3xl font-bold text-datadog-green">{formatCurrency(dynamicSavings)}</div>
								<div class="text-sm text-muted-foreground">per year ({dynamicSavingsPercent.toFixed(1)}% savings)</div>
							</div>
						</div>
					</div>
				{/if}
			</CardContent>
		</Card>
	{/if}

	<!-- Footer -->
	<footer class="mt-8 text-center text-sm text-muted-foreground">
		<p>
			Pricing data sourced from 
			<a href="https://www.datadoghq.com/pricing/list/" target="_blank" rel="noopener noreferrer" class="text-datadog-purple hover:underline">
				Datadog Pricing
			</a>
		</p>
	</footer>
</div>

<!-- Import Modal -->
{#if importModalOpen}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div 
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
		on:click|self={() => importModalOpen = false}
		on:keydown={(e) => e.key === 'Escape' && (importModalOpen = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div class="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl">
			<!-- Close Button -->
			<button
				type="button"
				class="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={() => importModalOpen = false}
			>
				<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>

			<h2 class="mb-2 text-xl font-semibold">Import Quote</h2>
			<p class="mb-6 text-sm text-muted-foreground">
				Drop a JSON file or click to select one
			</p>

			<!-- Drop Zone -->
			<div
				class="relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors {isDragging ? 'border-datadog-purple bg-datadog-purple/10' : 'border-border hover:border-muted-foreground'}"
				on:dragover={handleDragOver}
				on:dragleave={handleDragLeave}
				on:drop={handleDrop}
				role="button"
				tabindex="0"
			>
				<input
					type="file"
					accept=".json"
					class="absolute inset-0 cursor-pointer opacity-0"
					on:change={handleFileSelect}
				/>
				
				<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
					<svg class="h-8 w-8 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
						<polyline points="14 2 14 8 20 8" />
						<path d="M10 12l-2 2 2 2M14 12l2 2-2 2" />
					</svg>
				</div>
				
				<p class="text-center text-sm">
					<span class="font-medium text-datadog-purple">Click to upload</span>
					<span class="text-muted-foreground"> or drag and drop</span>
				</p>
				<p class="mt-1 text-xs text-muted-foreground">JSON files only</p>
			</div>

			{#if error}
				<p class="mt-4 text-sm text-red-500">{error}</p>
			{/if}
		</div>
	</div>
{/if}

<!-- Log Indexing Estimator Modal -->
{#if showLogsCalculator}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div 
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
		on:click|self={() => showLogsCalculator = false}
		on:keydown={(e) => e.key === 'Escape' && (showLogsCalculator = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div class="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl">
			<!-- Close Button -->
			<button
				type="button"
				class="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={() => showLogsCalculator = false}
			>
				<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>

			<LogsIndexingCalculator 
				{products} 
				onAddToQuote={(items) => {
					addItemsFromCalculator(items);
					showLogsCalculator = false;
				}}
			/>
		</div>
	</div>
{/if}

<!-- Save Quote Modal -->
{#if saveModalOpen}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div 
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
		on:click|self={() => saveModalOpen = false}
		on:keydown={(e) => e.key === 'Escape' && (saveModalOpen = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div class="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
			<!-- Close Button -->
			<button
				type="button"
				class="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={() => saveModalOpen = false}
			>
				<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>

			<div class="flex items-center gap-3 mb-6">
				<div class="flex h-11 w-11 items-center justify-center rounded-xl bg-datadog-purple shadow-lg shadow-datadog-purple/30">
					<svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
						<path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-semibold">Share Quote</h2>
					<p class="text-sm text-muted-foreground">Create a public URL for this quote</p>
				</div>
			</div>

			<!-- Quote Name -->
			<div class="mb-4">
				<label for="save-quote-name" class="mb-2 block text-sm font-medium">Quote Name</label>
				<Input 
					id="save-quote-name"
					bind:value={quoteName} 
					placeholder="My Datadog Quote" 
				/>
			</div>

			<!-- Password Protection Section -->
			<div class="rounded-xl border border-border bg-muted/30 p-4 mb-6">
				<div class="flex items-center gap-2 mb-3">
					<svg class="h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
						<path d="M7 11V7a5 5 0 0110 0v4" />
					</svg>
					<span class="text-sm font-medium">Edit Protection (Optional)</span>
				</div>
				<p class="text-xs text-muted-foreground mb-3">
					Set a password to prevent others from editing this quote. Anyone can still view it.
				</p>
				
				<div class="space-y-3">
					<div>
						<label for="edit-password" class="mb-1.5 block text-xs text-muted-foreground">Password</label>
						<Input 
							id="edit-password"
							type="password"
							bind:value={editPassword} 
							placeholder="Leave empty for no protection"
						/>
					</div>
					
					{#if editPassword}
						<div>
							<label for="confirm-password" class="mb-1.5 block text-xs text-muted-foreground">Confirm Password</label>
							<Input 
								id="confirm-password"
								type="password"
								bind:value={confirmPassword} 
								placeholder="Confirm password"
							/>
						</div>
					{/if}
				</div>
				
				{#if passwordError}
					<p class="mt-2 text-sm text-destructive">{passwordError}</p>
				{/if}
			</div>

			<!-- Actions -->
			<div class="flex gap-3">
				<Button 
					variant="outline" 
					class="flex-1"
					on:click={() => saveModalOpen = false}
				>
					Cancel
				</Button>
				<Button 
					class="flex-1 bg-datadog-purple hover:bg-datadog-purple/90"
					on:click={handleShare}
					disabled={saving || (editPassword !== '' && editPassword !== confirmPassword)}
				>
					{#if saving}
						<svg class="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M21 12a9 9 0 11-6.219-8.56" />
						</svg>
						Creating...
					{:else}
						<svg class="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
							<path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
						</svg>
						{editPassword ? 'Create Protected URL' : 'Create Public URL'}
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateX(-10px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}
</style>
