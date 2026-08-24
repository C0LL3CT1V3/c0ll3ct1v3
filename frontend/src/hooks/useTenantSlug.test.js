import { subdomainFromHostname } from './useTenantSlug';

describe('subdomainFromHostname', () => {
  test.each([
    ['localhost', ''],
    ['LOCALHOST', ''],
    ['www.localhost', ''],
    ['127.0.0.1', ''],
    ['192.168.1.10', ''],
    ['::1', ''],
    ['[::1]', ''],
    ['c0ll3ct1v3.xyz', ''],
    ['www.c0ll3ct1v3.xyz', ''],
    ['phillipjames.localhost', 'phillipjames'],
    ['phillip-james.localhost', 'phillip-james'],
    ['phillipjames.c0ll3ct1v3.xyz', 'phillipjames'],
    ['phillip-james.c0ll3ct1v3.xyz', 'phillip-james'],
    ['demo.localhost', 'demo'],
  ])('%s → %j', (hostname, expected) => {
    expect(subdomainFromHostname(hostname)).toBe(expected);
  });
});
