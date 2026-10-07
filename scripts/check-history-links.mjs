import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Execute the profile's relationship expression against conflicting serials.
const equipmentSource = readFileSync(new URL('../src/features/equipment.tsx', import.meta.url), 'utf8');
const relationship = equipmentSource.match(/const relatedServices=(.*);/)[1];
const equipmentServices = new Function('selected', 'data', `return ${relationship}`);
const selected = { id: 7, serialNumber: 'SHARED-SERIAL' };
const data = { services: [
  { id: 1, equipmentId: 7, serialNumber: 'SHARED-SERIAL' },
  { id: 2, equipmentId: 8, serialNumber: 'SHARED-SERIAL' },
  { id: 3, equipmentId: null, serialNumber: 'SHARED-SERIAL' },
  ...Array.from({ length: 12 }, (_, i) => ({ id: i + 4, equipmentId: 7, serialNumber: '' }))
] };
assert.deepEqual(equipmentServices(selected, data).map(s => s.id), [1, ...Array.from({ length: 12 }, (_, i) => i + 4)]);
assert.deepEqual(equipmentServices(null, data), []);

// Human-readable IDs are display labels; filtering uses internal record keys.
const clientSource = readFileSync(new URL('../src/features/clients.tsx', import.meta.url), 'utf8');
const ids = clientSource.match(/const serviceIds=(.*);/)[1];
const history = clientSource.match(/const filteredHistory=(.*);/)[1];
const filterHistory = new Function('filteredServices', 'equipmentFilter', 'history', `const serviceIds=${ids};return ${history}`);
const events = [{ serviceCallId: 1, serviceId: 'SRV-100' }, { serviceCallId: 2, serviceId: 'SRV-100' }];
assert.deepEqual(filterHistory([{ id: 1, serviceId: 'SRV-100' }], 7, events), [events[0]]);
assert.deepEqual(filterHistory([], 7, events), []);
assert.deepEqual(filterHistory([], 'all', events), events);
assert.ok(equipmentSource.includes('relatedServices.map('));
assert.ok(clientSource.includes('filteredServices.map('));
console.log('History relationship checks passed: shared serials, missing links, full lists, and internal history IDs.');
